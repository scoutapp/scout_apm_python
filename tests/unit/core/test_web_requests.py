# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import time

import pytest

from scout_apm.compat import datetime_to_timestamp
from scout_apm.core.context import AgentContext
from scout_apm.core.web_requests import (
    CUTOFF_EPOCH_S,
    convert_ambiguous_timestamp_to_ns,
    create_filtered_path,
    ignore_path,
    track_request_queue_time,
)


@pytest.fixture(autouse=True)
def force_context():
    # Since this function accesses the context, it needs to always be built
    # TODO: remove when moving to a sensible singleton pattern
    AgentContext.build()


@pytest.mark.parametrize(
    "path, params, expected",
    [
        ("/", [], "/"),
        ("/foo/", [], "/foo/"),
        ("/", [("bar", "1")], "/?bar=1"),
        ("/", [("baz", 2), ("bar", "1")], "/?bar=1&baz=2"),
        ("/", [("bar", "1"), ("bar", "2")], "/?bar=1&bar=2"),
        ("/", [("password", "hunter2")], "/?password=%5BFILTERED%5D"),
        ("/", [("PASSWORD", "hunter2")], "/?PASSWORD=%5BFILTERED%5D"),
        (
            "/",
            [("password", "hunter2"), ("password", "hunter3")],
            "/?password=%5BFILTERED%5D&password=%5BFILTERED%5D",
        ),
    ],
)
def test_create_filtered_path(path, params, expected):
    assert create_filtered_path(path, params) == expected


@pytest.mark.parametrize("path, params", [("/", []), ("/", [("foo", "ignored")])])
def test_create_filtered_path_path(path, params):
    # If config filtered_params is set to "path", expect we always get the path
    # back
    AgentContext.instance.config.set(uri_reporting="path")
    try:
        assert create_filtered_path(path, params) == path
    finally:
        AgentContext.instance.config.reset_all()


@pytest.mark.parametrize(
    "path, expected",
    [("/health", True), ("/health/foo", True), ("/users", False), ("/", False)],
)
def test_ignore(path, expected):
    AgentContext.instance.config.set(ignore=["/health"])

    try:
        result = ignore_path(path)
    finally:
        AgentContext.instance.config.reset_all()

    assert result == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/health", True),
        ("/health/foo", True),
        ("/api", True),
        ("/api/foo", True),
        ("/users", False),
        ("/", False),
    ],
)
def test_ignore_multiple_prefixes(path, expected):
    AgentContext.instance.config.set(ignore=["/health", "/api"])

    try:
        result = ignore_path(path)
    finally:
        AgentContext.instance.config.reset_all()

    assert result == expected


@pytest.mark.parametrize("with_t", [True, False])
def test_track_request_queue_time_valid(with_t, tracked_request):
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow()) - 2)
    if with_t:
        header_value = str("t=") + str(queue_start)
    else:
        header_value = str(queue_start)

    track_request_queue_time(header_value, tracked_request)
    queue_time_ns = tracked_request.tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


@pytest.mark.parametrize(
    "header_value",
    [
        str(""),
        str("t=X"),  # first character not a digit
        str("t=0.3f"),  # raises ValueError on float() conversion
        str(datetime_to_timestamp(dt.datetime.utcnow()) + 3600.0),  # one hour in future
        str(datetime_to_timestamp(dt.datetime(2009, 1, 1))),  # before ambig cutoff
    ],
)
def test_track_request_queue_time_invalid(header_value, tracked_request):
    track_request_queue_time(header_value, tracked_request)

    assert "scout.queue_time_ns" not in tracked_request.tags


ref_time_s = time.mktime((2019, 6, 1, 0, 0, 0, 0, 0, 0))


@pytest.mark.parametrize(
    "given,expected",
    [
        (ref_time_s, ref_time_s * 1e9),
        (ref_time_s * 1e3, ref_time_s * 1e9),
        (ref_time_s * 1e6, ref_time_s * 1e9),
        (CUTOFF_EPOCH_S + 10, (CUTOFF_EPOCH_S + 10) * 1e9),
        (0.0, 0.0),
        (1000.0, 0.0),
        (float("inf"), float("inf")),
        (float("-inf"), 0.0),
        (float("nan"), 0.0),
    ],
)
def test_convert_ambiguous_timestamp_to_ns(given, expected):
    assert convert_ambiguous_timestamp_to_ns(given) == expected
