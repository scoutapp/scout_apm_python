# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
from contextlib import contextmanager

import pytest
import redis

from scout_apm.instruments.redis import Instrument
from tests.compat import mock
from tests.tools import pretend_package_unavailable

# e.g. export REDIS_URL="redis://localhost:6379/0"
REDIS_URL = os.environ.get("REDIS_URL")
skip_if_redis_not_running = pytest.mark.skipif(
    REDIS_URL is None, reason="Redis isn't available"
)
pytestmark = [skip_if_redis_not_running]

instrument = Instrument()


@contextmanager
def redis_with_scout():
    """
    Create an instrumented Redis connection.

    """
    r = redis.Redis.from_url(REDIS_URL)
    instrument.install()
    try:
        yield r
    finally:
        instrument.uninstall()
        pass


def test_echo():
    with redis_with_scout() as r:
        r.echo("Hello World!")


def test_pipe_echo():
    with redis_with_scout() as r:
        with r.pipeline() as p:
            p.echo("Hello World!")
            p.execute()


def test_perform_request_missing_url():
    with redis_with_scout() as r:
        with pytest.raises(IndexError):
            # Redis instrumentation doesn't crash if op is missing.
            # This raises a TypeError (Python 3) or IndexError (Python 2)
            # when calling the original method.
            r.execute_command()


def test_perform_request_bad_url():
    with redis_with_scout() as r:
        with pytest.raises(TypeError):
            # Redis instrumentation doesn't crash if op has the wrong type.
            # This raises a TypeError when calling the original method.
            r.execute_command(None)


def test_installed():
    with redis_with_scout():
        assert Instrument.installed
    assert not Instrument.installed


def test_installable():
    with redis_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_redis_module():
    with mock.patch("scout_apm.instruments.redis.redis", new=None):
        assert not instrument.installable()


def test_install_no_redis_module():
    with mock.patch("scout_apm.instruments.redis.redis", new=None):
        assert not instrument.install()
        assert not Instrument.installed


def test_patch_redis_no_redis_module():
    with pretend_package_unavailable("redis"):
        instrument.patch_redis()  # doesn't crash


@mock.patch("scout_apm.instruments.redis.Redis")
def test_patch_redis_install_failure(mock_redis, caplog):
    del mock_redis.execute_command
    instrument.patch_redis()  # doesn't crash
    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.redis",
            logging.WARNING,
            (
                "Unable to instrument for Redis Redis.execute_command: "
                + "AttributeError('execute_command')"
            ),
        )
    ]


def test_patch_pipeline_no_redis_module():
    with pretend_package_unavailable("redis"):
        instrument.patch_pipeline()  # doesn't crash


@mock.patch("scout_apm.instruments.redis.Pipeline")
def test_patch_pipeline_install_failure(mock_pipeline, caplog):
    del mock_pipeline.execute
    instrument.patch_pipeline()  # doesn't crash
    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.redis",
            30,
            (
                "Unable to instrument for Redis BasePipeline.execute: "
                + "AttributeError('execute')"
            ),
        )
    ]


def test_install_is_idempotent():
    with redis_with_scout():
        assert Instrument.installed
        instrument.install()  # does nothing, doesn't crash
        assert Instrument.installed


def test_uninstall_is_idempotent():
    assert not Instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
    assert not Instrument.installed
