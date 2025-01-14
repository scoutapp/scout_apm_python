# coding=utf-8

from unittest import mock

import pytest

from scout_apm.core.config import ScoutConfig
from scout_apm.core.sampler import Sampler
from scout_apm.core.tracked_request import TrackedRequest


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


@pytest.fixture
def tracked_request():
    return TrackedRequest()


def test_should_sample_endpoint_always(sampler, tracked_request):
    tracked_request.operation = "Controller/users"
    assert sampler.should_sample(tracked_request) is True


def test_should_sample_endpoint_never(sampler, tracked_request):
    tracked_request.operation = "Controller/health/check"
    assert sampler.should_sample(tracked_request) is False
    tracked_request.operation = "Controller/users/test"
    assert sampler.should_sample(tracked_request) is False


def test_should_sample_endpoint_ignored(sampler, tracked_request):
    tracked_request.operation = "Controller/metrics"
    assert sampler.should_sample(tracked_request) is False


def test_should_sample_endpoint_partial(sampler, tracked_request):
    tracked_request.operation = "Controller/test/endpoint"
    with mock.patch("random.randint", return_value=10):
        assert sampler.should_sample(tracked_request) is True
    with mock.patch("random.randint", return_value=30):
        assert sampler.should_sample(tracked_request) is False


def test_should_sample_job_always(sampler, tracked_request):
    tracked_request.operation = "Job/critical-job"
    assert sampler.should_sample(tracked_request) is True


def test_should_sample_job_never(sampler, tracked_request):
    tracked_request.operation = "Job/test-job"
    assert sampler.should_sample(tracked_request) is False


def test_should_sample_job_partial(sampler, tracked_request):
    tracked_request.operation = "Job/batch-process"
    with mock.patch("random.randint", return_value=10):
        assert sampler.should_sample(tracked_request) is True
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample(tracked_request) is False


def test_should_sample_unknown_operation(sampler, tracked_request):
    tracked_request.operation = "Unknown/operation"
    with mock.patch("random.randint", return_value=10):
        assert sampler.should_sample(tracked_request) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample(tracked_request) is False


def test_should_sample_no_sampling_enabled(config, tracked_request):
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
    tracked_request.operation = "Controller/any_endpoint"
    assert sampler.should_sample(tracked_request) is True
    tracked_request.operation = "Job/any_job"
    assert sampler.should_sample(tracked_request) is True


def test_should_sample_endpoint_default_rate(sampler, tracked_request):
    tracked_request.operation = "Controller/unspecified"
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample(tracked_request) is True
    with mock.patch("random.randint", return_value=80):
        assert sampler.should_sample(tracked_request) is False


def test_should_sample_job_default_rate(sampler, tracked_request):
    tracked_request.operation = "Job/unspecified-job"
    with mock.patch("random.randint", return_value=30):
        assert sampler.should_sample(tracked_request) is True
    with mock.patch("random.randint", return_value=50):
        assert sampler.should_sample(tracked_request) is False


def test_should_sample_endpoint_fallback_to_global_rate(config, tracked_request):
    config.set(endpoint_sample_rate=None)
    sampler = Sampler(config)
    tracked_request.operation = "Controller/unspecified"
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample(tracked_request) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample(tracked_request) is False


def test_should_sample_job_fallback_to_global_rate(config, tracked_request):
    config.set(job_sample_rate=None)
    sampler = Sampler(config)
    tracked_request.operation = "Job/unspecified-job"
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample(tracked_request) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample(tracked_request) is False


def test_should_handle_legacy_ignore_with_specific_sampling(config, tracked_request):
    """Test that specific sampling rates override legacy ignore patterns."""
    config.set(
        ignore=["foo"],
        sample_endpoints={
            "foo/bar": 50  # Should override the ignore pattern for specific endpoint
        },
    )
    sampler = Sampler(config)

    # foo/bar should be sampled at 50%
    tracked_request.operation = "Controller/foo/bar"
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample(tracked_request) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample(tracked_request) is False

    # foo/other should be ignored (0% sampling)
    tracked_request.operation = "Controller/foo/other"
    assert sampler.should_sample(tracked_request) is False


def test_prefix_matching_precedence(config, tracked_request):
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
    tracked_request.operation = "Controller/api/status"
    assert sampler.should_sample(tracked_request) is False

    # Users API should be sampled at 50%
    tracked_request.operation = "Controller/api/users/list"
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample(tracked_request) is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample(tracked_request) is False

    # VIP users API should always be sampled
    tracked_request.operation = "Controller/api/users/vip/list"
    assert sampler.should_sample(tracked_request) is True
