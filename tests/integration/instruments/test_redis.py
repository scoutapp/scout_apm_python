# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

import pytest
import redis

from scout_apm.instruments.redis import install
from tests.compat import mock

# e.g. export REDIS_URL="redis://localhost:6379/0"
REDIS_URL = os.environ.get("REDIS_URL")
skip_if_redis_not_running = pytest.mark.skipif(
    REDIS_URL is None, reason="Redis isn't available"
)
pytestmark = [skip_if_redis_not_running]


@pytest.fixture
def ensure_installed():
    # Should always successfully install in our test environment
    install()
    yield


@pytest.fixture
def redis_conn():
    yield redis.Redis.from_url(REDIS_URL)


mock_not_attempted = mock.patch("scout_apm.instruments.redis.attempted", new=False)


def test_install_fail_already_attempted(ensure_installed, caplog):
    result = install()

    assert result is False
    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.redis",
            logging.WARNING,
            "Redis instrumentation has already been attempted to be installed.",
        )
    ]


def test_install_fail_no_redis(caplog):
    mock_no_redis = mock.patch("scout_apm.instruments.redis.redis", new=None)
    with mock_not_attempted, mock_no_redis:
        result = install()

    assert result is False
    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.redis",
            logging.INFO,
            "Unable to import Redis",
        )
    ]


def test_install_success_no_redis_execute_command(caplog):
    mock_redis = mock.patch("scout_apm.instruments.redis.Redis")
    with mock_not_attempted, mock_redis as mocked_redis:
        del mocked_redis.execute_command

        result = install()

    assert result is True
    assert len(caplog.record_tuples) == 1
    logger, level, message = caplog.record_tuples[0]
    assert logger == "scout_apm.instruments.redis"
    assert level == logging.WARNING
    assert message.startswith(
        "Unable to instrument for Redis Redis.execute_command: AttributeError"
    )


def test_install_success_no_pipeline_execute(caplog):
    mock_pipeline = mock.patch("scout_apm.instruments.redis.Pipeline")
    with mock_not_attempted, mock_pipeline as mocked_pipeline:
        del mocked_pipeline.execute

        result = install()

    assert result is True
    assert len(caplog.record_tuples) == 1
    logger, level, message = caplog.record_tuples[0]
    assert logger == "scout_apm.instruments.redis"
    assert level == logging.WARNING
    assert message.startswith(
        "Unable to instrument for Redis Pipeline.execute: AttributeError"
    )


def test_echo(ensure_installed, redis_conn, tracked_request):
    redis_conn = redis_conn.echo("Hello World!")

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Redis/Echo"


def test_pipeline_echo(ensure_installed, redis_conn, tracked_request):
    with redis_conn.pipeline() as p:
        p.echo("Hello World!")
        p.execute()

    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Redis/Echo"
    assert tracked_request.complete_spans[1].operation == "Redis/MULTI"


# def test_perform_request_missing_url():
#     with redis_with_scout() as r:
#         with pytest.raises(IndexError):
#             # Redis instrumentation doesn't crash if op is missing.
#             # This raises a TypeError (Python 3) or IndexError (Python 2)
#             # when calling the original method.
#             r.execute_command()


# def test_perform_request_bad_url():
#     with redis_with_scout() as r:
#         with pytest.raises(TypeError):
#             # Redis instrumentation doesn't crash if op has the wrong type.
#             # This raises a TypeError when calling the original method.
#             r.execute_command(None)


# def test_installed():
#     with redis_with_scout():
#         assert Instrument.installed
#     assert not Instrument.installed


# def test_installable():
#     with redis_with_scout():
#         assert not instrument.installable()
#     assert instrument.installable()


# def test_installable_no_redis_module():
#     with mock.patch("scout_apm.instruments.redis.redis", new=None):
#         assert not instrument.installable()


# def test_install_no_redis_module():
#     with mock.patch("scout_apm.instruments.redis.redis", new=None):
#         assert not instrument.install()
#         assert not Instrument.installed


# def test_patch_redis_no_redis_module():
#     with pretend_package_unavailable("redis"):
#         instrument.patch_redis()  # doesn't crash


# @mock.patch("scout_apm.instruments.redis.Redis")
# def test_patch_redis_install_failure(mock_redis, caplog):
#     del mock_redis.execute_command
#     instrument.patch_redis()  # doesn't crash
#     assert len(caplog.record_tuples) == 1
#     logger, level, message = caplog.record_tuples[0]
#     assert logger == "scout_apm.instruments.redis"
#     assert level == logging.WARNING
#     assert message.startswith(
#         "Unable to instrument for Redis Redis.execute_command: AttributeError"
#     )


# def test_patch_pipeline_no_redis_module():
#     with pretend_package_unavailable("redis"):
#         instrument.patch_pipeline()  # doesn't crash


# @mock.patch("scout_apm.instruments.redis.Pipeline")
# def test_patch_pipeline_install_failure(mock_pipeline, caplog):
#     del mock_pipeline.execute
#     instrument.patch_pipeline()  # doesn't crash

#     assert len(caplog.record_tuples) == 1
#     logger, level, message = caplog.record_tuples[0]
#     assert logger == "scout_apm.instruments.redis"
#     assert level == logging.WARNING
#     assert message.startswith(
#         "Unable to instrument for Redis BasePipeline.execute: AttributeError"
#     )


# def test_install_is_idempotent():
#     with redis_with_scout():
#         assert Instrument.installed
#         instrument.install()  # does nothing, doesn't crash
#         assert Instrument.installed


# def test_uninstall_is_idempotent():
#     assert not Instrument.installed
#     instrument.uninstall()  # does nothing, doesn't crash
#     assert not Instrument.installed
