# coding=utf-8

from scout_apm.core.stacktracer import trace_method


class TraceMe(object):
    def trace_me(self, *args, **kwargs):
        return args, kwargs


def trace_me(*args, **kwargs):
    return args, kwargs


def test_trace_method(tracked_request):
    @trace_method(TraceMe)
    def trace_me(self, *args, **kwargs):
        return ("Test/Method", {"name": "trace_me"})

    try:
        TraceMe().trace_me()
    finally:
        TraceMe.trace_me = TraceMe.trace_me.__wrapped__

    span = tracked_request.complete_spans[0]
    assert span.operation == "Test/Method/trace_me"


def test_trace_method_no_name(tracked_request):
    @trace_method(TraceMe)
    def trace_me(self, *args, **kwargs):
        return ("Test/Method", {"name": None})

    try:
        TraceMe().trace_me()
    finally:
        TraceMe.trace_me = TraceMe.trace_me.__wrapped__

    span = tracked_request.complete_spans[0]
    assert span.operation == "Test/Method"
