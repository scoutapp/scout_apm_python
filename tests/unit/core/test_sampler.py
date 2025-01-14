# coding=utf-8

from unittest import mock

import pytest

from scout_apm.core.config import ScoutConfig
from scout_apm.core.sampler import Sampler


@pytest.fixture
def config():
    config = ScoutConfig()
    ScoutConfig.set(
        sample_rate=50,  # 50% global sampling
        sample_endpoints={
            "users": 100,  # Always sample
            "test": 20,  # 20% sampling for test endpoints
            "health": 0,  # Never sample health checks
        },
        sample_jobs={
            "critical-job": 100,  # Always sample
            "batch": 30,  # 30% sampling for batch jobs
        },
        ignore_endpoints=["metrics", "ping", "users/test"],
        ignore_jobs=["test-job"],
        endpoint_sample_rate=70,  # 70% sampling for unspecified endpoints
        job_sample_rate=40,  # 40% sampling for unspecified jobs
    )
    yield config
    ScoutConfig.reset_all()


@pytest.fixture
def sampler(config):
    return Sampler(config)


def test_should_sample_endpoint_always(sampler):
    assert sampler.should_sample("Controller/users", False) is True


def test_should_sample_endpoint_never(sampler):
    assert sampler.should_sample("Controller/health/check", False) is False
    assert sampler.should_sample("Controller/users/test", False) is False


def test_should_sample_endpoint_ignored(sampler):
    assert sampler.should_sample("Controller/metrics", False) is False


def test_should_sample_endpoint_partial(sampler):
    with mock.patch("random.randint", return_value=10):
        assert sampler.should_sample("Controller/test/endpoint", False) is True
    with mock.patch("random.randint", return_value=30):
        assert sampler.should_sample("Controller/test/endpoint", False) is False


def test_should_sample_job_always(sampler):
    assert sampler.should_sample("Job/critical-job", False) is True


def test_should_sample_job_never(sampler):
    assert sampler.should_sample("Job/test-job", False) is False


def test_should_sample_job_partial(sampler):
    with mock.patch("random.randint", return_value=10):
        assert sampler.should_sample("Job/batch-process", False) is True
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample("Job/batch-process", False) is False


def test_should_sample_unknown_operation(sampler):
    with mock.patch("random.randint", return_value=10):
        assert sampler.should_sample("Unknown/operation", False) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Unknown/operation", False) is False


def test_should_sample_no_sampling_enabled(config):
    config.set(
        sample_rate=100,  # Return config to defaults
        sample_endpoints={},
        sample_jobs={},
        ignore_endpoints=[],
        ignore_jobs=[],
        endpoint_sample_rate=None,
        job_sample_rate=None,
    )
    sampler = Sampler(config)
    assert sampler.should_sample("Controller/any_endpoint", False) is True
    assert sampler.should_sample("Job/any_job", False) is True


def test_should_sample_endpoint_default_rate(sampler):
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Controller/unspecified", False) is True
    with mock.patch("random.randint", return_value=80):
        assert sampler.should_sample("Controller/unspecified", False) is False


def test_should_sample_job_default_rate(sampler):
    with mock.patch("random.randint", return_value=30):
        assert sampler.should_sample("Job/unspecified-job", False) is True
    with mock.patch("random.randint", return_value=50):
        assert sampler.should_sample("Job/unspecified-job", False) is False


def test_should_sample_endpoint_fallback_to_global_rate(config):
    config.set(endpoint_sample_rate=None)
    sampler = Sampler(config)
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample("Controller/unspecified", False) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Controller/unspecified", False) is False


def test_should_sample_job_fallback_to_global_rate(config):
    config.set(job_sample_rate=None)
    sampler = Sampler(config)
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample("Job/unspecified-job", False) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Job/unspecified-job", False) is False


def test_should_handle_legacy_ignore_with_specific_sampling(config):
    """Test that specific sampling rates override legacy ignore patterns."""
    config.set(
        ignore=["foo"],
        sample_endpoints={
            "foo/bar": 50  # Should override the ignore pattern for specific endpoint
        },
    )
    sampler = Sampler(config)

    # foo/bar should be sampled at 50%
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample("Controller/foo/bar", False) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Controller/foo/bar", False) is False

    # foo/other should be ignored (0% sampling)
    assert sampler.should_sample("Controller/foo/other", False) is False


def test_prefix_matching_precedence(config):
    """Test that longer prefix matches take precedence."""
    config.set(
        sample_endpoints={
            "api": 0,  # Ignore all API endpoints by default
            "api/users": 50,  # Sample 50% of user endpoints
            "api/users/vip": 100,  # Sample all VIP user endpoints
        }
    )
    sampler = Sampler(config)

    # Regular API endpoint should be ignored
    assert sampler.should_sample("Controller/api/status", False) is False

    # Users API should be sampled at 50%
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample("Controller/api/users/list", False) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Controller/api/users/list", False) is False

    # VIP users API should always be sampled
    assert sampler.should_sample("Controller/api/users/vip/list", False) is True
