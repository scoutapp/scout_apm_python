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
        ignore_endpoints=["metrics", "ping"],
        ignore_jobs=["test-job"],
        sample_endpoint_rate=70,  # 70% sampling for unspecified endpoints
        sample_job_rate=40,  # 40% sampling for unspecified jobs
    )
    yield config
    ScoutConfig.reset_all()


@pytest.fixture
def sampler(config):
    return Sampler(config)


def test_should_sample_endpoint_always(sampler):
    assert sampler.should_sample("Controller/users") is True


def test_should_sample_endpoint_never(sampler):
    assert sampler.should_sample("Controller/health/check") is False


def test_should_sample_endpoint_ignored(sampler):
    assert sampler.should_sample("Controller/metrics") is False


def test_should_sample_endpoint_partial(sampler):
    with mock.patch("random.randint", return_value=10):
        assert sampler.should_sample("Controller/test/endpoint") is True
    with mock.patch("random.randint", return_value=30):
        assert sampler.should_sample("Controller/test/endpoint") is False


def test_should_sample_job_always(sampler):
    assert sampler.should_sample("Job/critical-job") is True


def test_should_sample_job_never(sampler):
    assert sampler.should_sample("Job/test-job") is False


def test_should_sample_job_partial(sampler):
    with mock.patch("random.randint", return_value=10):
        assert sampler.should_sample("Job/batch-process") is True
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample("Job/batch-process") is False


def test_should_sample_unknown_operation(sampler):
    with mock.patch("random.randint", return_value=10):
        assert sampler.should_sample("Unknown/operation") is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Unknown/operation") is False


def test_should_sample_no_sampling_enabled(config):
    config.set(
        sample_rate=100,  # Return config to defaults
        sample_endpoints={},
        sample_jobs={},
        ignore_endpoints=[],
        ignore_jobs=[],
    )
    sampler = Sampler(config)
    assert sampler.should_sample("Controller/any_endpoint") is True
    assert sampler.should_sample("Job/any_job") is True


def test_should_sample_endpoint_default_rate(sampler):
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Controller/unspecified") is True
    with mock.patch("random.randint", return_value=80):
        assert sampler.should_sample("Controller/unspecified") is False


def test_should_sample_job_default_rate(sampler):
    with mock.patch("random.randint", return_value=30):
        assert sampler.should_sample("Job/unspecified-job") is True
    with mock.patch("random.randint", return_value=50):
        assert sampler.should_sample("Job/unspecified-job") is False


def test_should_sample_endpoint_fallback_to_global_rate(config):
    config.set(sample_endpoint_rate=None)
    sampler = Sampler(config)
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample("Controller/unspecified") is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Controller/unspecified") is False


def test_should_sample_job_fallback_to_global_rate(config):
    config.set(sample_job_rate=None)
    sampler = Sampler(config)
    with mock.patch("random.randint", return_value=40):
        assert sampler.should_sample("Job/unspecified-job") is True
    with mock.patch("random.randint", return_value=60):
        assert sampler.should_sample("Job/unspecified-job") is False
