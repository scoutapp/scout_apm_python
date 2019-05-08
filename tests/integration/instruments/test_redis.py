# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
from contextlib import contextmanager

import pytest
import redis

from scout_apm.instruments.redis import Instrument

try:
    from unittest.mock import patch
except ImportError:  # Python 2
    from mock import patch


# e.g. export REDIS_URL="redis://localhost:6379/0"
REDIS_URL = os.environ.get("REDIS_URL")
if REDIS_URL is None:
    pytest.skip("Redis isn't available", allow_module_level=True)


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


@contextmanager
def no_redis():
    sys.modules["redis"] = None
    sys.modules["redis.client"] = None
    try:
        yield
    finally:
        sys.modules["redis"] = redis
        sys.modules["redis.client"] = redis.client


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
    assert not instrument.installed
    with redis_with_scout():
        assert instrument.installed
    assert not instrument.installed


def test_installable():
    assert instrument.installable()
    with redis_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_redis_module():
    with no_redis():
        assert not instrument.installable()


def test_install_no_redis_module():
    with no_redis():
        assert not instrument.install()
        assert not instrument.installed


def test_patch_redis_no_redis_module():
    with no_redis():
        instrument.patch_redis()  # doesn't crash


@patch("scout_apm.instruments.redis.monkeypatch_method", side_effect=RuntimeError)
def test_patch_redis_install_failure(monkeypatch_method):
    instrument.patch_redis()  # doesn't crash


def test_patch_pipeline_no_redis_module():
    with no_redis():
        instrument.patch_pipeline()  # doesn't crash


@patch("scout_apm.instruments.redis.monkeypatch_method", side_effect=RuntimeError)
def test_patch_pipeline_install_failure(monkeypatch_method):
    instrument.patch_pipeline()  # doesn't crash


def test_install_is_idempotent():
    with redis_with_scout():
        assert instrument.installed
        instrument.install()  # does nothing, doesn't crash


def test_uninstall_is_idempotent():
    assert not instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
