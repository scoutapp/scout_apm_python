# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import time

import pytest

from scout_apm.core.samplers.thread import SamplersThread


@pytest.fixture(autouse=True)
def ensure_stopped_before_and_after():
    SamplersThread.ensure_stopped()
    try:
        yield
    finally:
        assert not SamplersThread._stop_event.is_set()
        SamplersThread.ensure_stopped()


def test_ensure_started(caplog):
    SamplersThread.ensure_started()
    time.sleep(0.001)

    assert SamplersThread._instance is not None
    assert caplog.record_tuples[0] == (
        "scout_apm.core.samplers.thread",
        10,
        "Starting Samplers.",
    )


def test_ensure_stopped(caplog):
    SamplersThread.ensure_started()
    time.sleep(0.001)
    SamplersThread.ensure_stopped()

    assert SamplersThread._instance is None
    assert caplog.record_tuples[-1] == (
        "scout_apm.core.samplers.thread",
        10,
        "Stopping Samplers.",
    )
