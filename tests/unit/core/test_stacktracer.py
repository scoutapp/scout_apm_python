# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.core.stacktracer import trace_function, trace_method
from scout_apm.core.tracked_request import TrackedRequest
from tests.compat import mock


class TraceMe(object):
    def trace_me(self, *args, **kwargs):
        return args, kwargs


def trace_me(*args, **kwargs):
    return args, kwargs


@pytest.fixture
def tracked_request():
    request = TrackedRequest.instance()
    request.start_span()  # prevent request from finalizing
    try:
        yield request
    finally:
        request.stop_span()


def test_trace_function(tracked_request):
    traced = trace_function(trace_me, ("Test/Function", {"name": "trace_me"}))
    traced()

    span = tracked_request.complete_spans[0]
    assert span.operation == "Test/Function/trace_me"


def test_trace_function_callable_info(tracked_request):
    traced = trace_function(trace_me, lambda: ("Test/Function", {"name": "trace_me"}))
    traced()

    span = tracked_request.complete_spans[0]
    assert span.operation == "Test/Function/trace_me"


@mock.patch("scout_apm.core.stacktracer.wrapt.decorator", side_effect=RuntimeError)
def test_trace_function_exception(mock_decorator, tracked_request):
    traced = trace_function(trace_me, lambda: ("Test/Function", {"name": "trace_me"}))
    assert traced is trace_me  # patching failed


def test_trace_function_no_name(tracked_request):
    traced = trace_function(trace_me, ("Test/Function", {"name": None}))
    traced()

    span = tracked_request.complete_spans[0]
    assert span.operation == "Test/Function"


def test_trace_method(tracked_request):
    @trace_method(TraceMe)  # noqa: F811
    def trace_me(self, *args, **kwargs):
        return ("Test/Method", {"name": "trace_me"})

    try:
        TraceMe().trace_me()
    finally:
        TraceMe.trace_me = TraceMe.trace_me.__wrapped__

    span = tracked_request.complete_spans[0]
    assert span.operation == "Test/Method/trace_me"


def test_trace_method_no_name(tracked_request):
    @trace_method(TraceMe)  # noqa: F811
    def trace_me(self, *args, **kwargs):
        return ("Test/Method", {"name": None})

    try:
        TraceMe().trace_me()
    finally:
        TraceMe.trace_me = TraceMe.trace_me.__wrapped__

    span = tracked_request.complete_spans[0]
    assert span.operation == "Test/Method"
