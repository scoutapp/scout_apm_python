# coding=utf-8

import logging
import os

import pytest
import redis

from scout_apm.instruments.redis import ensure_installed
from tests.compat import mock


@pytest.fixture(scope="module")
def redis_conn():
    ensure_installed()
    # e.g. export REDIS_URL="redis://localhost:6379/0"
    if "REDIS_URL" not in os.environ:
        raise pytest.skip("Redis isn't available")
    yield redis.Redis.from_url(os.environ["REDIS_URL"])


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    assert caplog.record_tuples == 2 * [
        (
            "scout_apm.instruments.redis",
            logging.DEBUG,
            "Instrumenting redis.",
        )
    ]


def test_install_fail_no_redis(caplog):
    mock_no_redis = mock.patch("scout_apm.instruments.redis.redis", new=None)
    with mock_no_redis:
        ensure_installed()

    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.redis",
            logging.DEBUG,
            "Instrumenting redis.",
        ),
        (
            "scout_apm.instruments.redis",
            logging.DEBUG,
            "Couldn't import redis - probably not installed.",
        ),
    ]


def test_ensure_installed_fail_no_redis_execute_command(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.redis.have_patched_redis_execute_command", new=False
    )
    mock_redis = mock.patch("scout_apm.instruments.redis.Redis")
    with mock_not_patched, mock_redis as mocked_redis:
        del mocked_redis.execute_command

        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.redis",
        logging.DEBUG,
        "Instrumenting redis.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.redis"
    assert level == logging.WARNING
    assert message.startswith(
        "Failed to instrument redis.Redis.execute_command: AttributeError"
    )


def test_ensure_installed_fail_no_pipeline_execute(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.redis.have_patched_pipeline_execute", new=False
    )
    mock_pipeline = mock.patch("scout_apm.instruments.redis.Pipeline")
    with mock_not_patched, mock_pipeline as mocked_pipeline:
        del mocked_pipeline.execute

        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.redis",
        logging.DEBUG,
        "Instrumenting redis.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.redis"
    assert level == logging.WARNING
    assert message.startswith(
        "Failed to instrument redis.Pipeline.execute: AttributeError"
    )


def test_echo(redis_conn, tracked_request):
    redis_conn.echo("Hello World!")

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Redis/ECHO"


def test_pipeline_echo(redis_conn, tracked_request):
    with redis_conn.pipeline() as p:
        p.echo("Hello World!")
        p.execute()

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Redis/MULTI"


def test_execute_command_missing_argument(redis_conn, tracked_request):
    # Redis instrumentation doesn't crash if op is missing.
    # This raises a TypeError (Python 3) or IndexError (Python 2)
    # when calling the original method.
    with pytest.raises(IndexError):
        redis_conn.execute_command()

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Redis/Unknown"


def test_perform_request_bad_url(redis_conn, tracked_request):
    with pytest.raises(TypeError):
        # Redis instrumentation doesn't crash if op has the wrong type.
        # This raises a TypeError when calling the original method.
        redis_conn.execute_command(None)

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Redis/None"
