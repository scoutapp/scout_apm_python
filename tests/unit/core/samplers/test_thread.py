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

    assert caplog.record_tuples[0] == (
        "scout_apm.core.samplers.thread",
        10,
        "Starting Samplers.",
    )


def test_ensure_stopped(caplog):
    SamplersThread.ensure_started()
    time.sleep(0.001)
    SamplersThread.ensure_stopped()

    # Ignore logs from the core agent thread.
    records = [
        record
        for record in caplog.record_tuples
        if record[0] == "scout_apm.core.samplers.thread"
    ]
    assert records[-1] == (
        "scout_apm.core.samplers.thread",
        10,
        "Stopping Samplers.",
    )
