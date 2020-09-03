# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

import aioredis
import pytest

from scout_apm.instruments.aioredis import ensure_installed
from tests.compat import mock
from tests.tools import async_test


async def get_redis_conn():
    ensure_installed()
    # e.g. export REDIS_URL="redis://localhost:6379/0"
    if "REDIS_URL" not in os.environ:
        raise pytest.skip("Redis isn't available")
    conn = await aioredis.create_connection(os.environ["REDIS_URL"])
    return aioredis.Redis(conn)


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    assert caplog.record_tuples == 2 * [
        (
            "scout_apm.instruments.aioredis",
            logging.DEBUG,
            "Instrumenting aioredis.",
        )
    ]


def test_ensure_installed_fail_no_redis_execute(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.aioredis.have_patched_redis_execute", new=False
    )
    mock_redis = mock.patch("scout_apm.instruments.aioredis.Redis")
    with mock_not_patched, mock_redis as mocked_redis:
        del mocked_redis.execute

        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.aioredis",
        logging.DEBUG,
        "Instrumenting aioredis.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.aioredis"
    assert level == logging.WARNING
    assert message.startswith(
        "Failed to instrument aioredis.Redis.execute: AttributeError"
    )


def test_ensure_installed_fail_no_wrapped_redis_execute(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.aioredis.have_patched_redis_execute", new=False
    )
    mock_wrapped_redis_execute = mock.patch(
        "scout_apm.instruments.aioredis.wrapped_redis_execute", new=None
    )
    with mock_not_patched, mock_wrapped_redis_execute:
        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.aioredis",
        logging.DEBUG,
        "Instrumenting aioredis.",
    )
    assert caplog.record_tuples[1] == (
        "scout_apm.instruments.aioredis",
        logging.DEBUG,
        (
            "Couldn't import scout_apm.async_.instruments.aioredis - probably"
            + " using Python < 3.6."
        ),
    )


def test_ensure_installed_fail_no_pipeline_execute(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.aioredis.have_patched_pipeline_execute", new=False
    )
    mock_pipeline = mock.patch("scout_apm.instruments.aioredis.Pipeline")
    with mock_not_patched, mock_pipeline as mocked_pipeline:
        del mocked_pipeline.execute

        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.aioredis",
        logging.DEBUG,
        "Instrumenting aioredis.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.aioredis"
    assert level == logging.WARNING
    assert message.startswith(
        "Failed to instrument aioredis.commands.Pipeline.execute: AttributeError"
    )


def test_ensure_installed_fail_no_wrapped_pipeline_execute(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.aioredis.have_patched_pipeline_execute", new=False
    )
    mock_wrapped_pipeline_execute = mock.patch(
        "scout_apm.instruments.aioredis.wrapped_pipeline_execute", new=None
    )
    with mock_not_patched, mock_wrapped_pipeline_execute:
        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.aioredis",
        logging.DEBUG,
        "Instrumenting aioredis.",
    )
    assert caplog.record_tuples[1] == (
        "scout_apm.instruments.aioredis",
        logging.DEBUG,
        (
            "Couldn't import scout_apm.async_.instruments.aioredis -"
            + " probably using Python < 3.6."
        ),
    )


@async_test
async def test_echo(tracked_request):
    redis_conn = await get_redis_conn()

    await redis_conn.echo("Hello World!")

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Redis/ECHO"


# def test_pipeline_echo(redis_conn, tracked_request):
#     with redis_conn.pipeline() as p:
#         p.echo("Hello World!")
#         p.execute()

#     assert len(tracked_request.complete_spans) == 1
#     assert tracked_request.complete_spans[0].operation == "Redis/MULTI"


# def test_execute_command_missing_argument(redis_conn, tracked_request):
#     # Redis instrumentation doesn't crash if op is missing.
#     # This raises a TypeError (Python 3) or IndexError (Python 2)
#     # when calling the original method.
#     with pytest.raises(IndexError):
#         redis_conn.execute_command()

#     assert len(tracked_request.complete_spans) == 1
#     assert tracked_request.complete_spans[0].operation == "Redis/Unknown"


# def test_perform_request_bad_url(redis_conn, tracked_request):
#     with pytest.raises(TypeError):
#         # Redis instrumentation doesn't crash if op has the wrong type.
#         # This raises a TypeError when calling the original method.
#         redis_conn.execute_command(None)

#     assert len(tracked_request.complete_spans) == 1
#     assert tracked_request.complete_spans[0].operation == "Redis/None"
