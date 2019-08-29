# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import pytest

from scout_apm.core.samplers.memory import Memory


@pytest.mark.parametrize(
    "given, expected",
    [
        (0, 0.0),
        (1024 * 1024, 1.0),
        (2 * 1024 * 1024, 2.0),
        (2 * 1024 * 1024 + 1, 2.0000009536743164),
    ],
)
def test_rss_to_mb(given, expected):
    assert Memory.rss_to_mb(given) == expected


def test_rss():
    result = Memory.rss()
    assert isinstance(result, int) and result > 0


def test_rss_in_mb():
    result = Memory.rss_in_mb()
    assert isinstance(result, float) and result > 0.0


def test_get_delta():
    result = Memory.get_delta(1.0)
    assert isinstance(result, float) and result > 0.0


def test_get_delta_big():
    result = Memory.get_delta(1e12)
    assert result == 0.0


def test_metric_type():
    assert Memory().metric_type() == "Memory"


def test_metric_name():
    assert Memory().metric_name() == "Physical"


def test_human_name():
    assert Memory().human_name() == "Process Memory"


def test_run(caplog):
    caplog.set_level(logging.DEBUG)

    result = Memory().run()
    assert isinstance(result, float) and result > 0.0
    record_tuples = [
        r for r in caplog.record_tuples if r[0] == "scout_apm.core.samplers.memory"
    ]
    assert len(record_tuples) == 1
    _, level, message = record_tuples[0]
    assert level == logging.DEBUG
    assert message.startswith("Process Memory: #")
