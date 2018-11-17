from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from scout_apm.core.monkey import CallableProxy, monkeypatch_method
from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)


def trace_method(cls, method_name=None):
    def decorator(info_func):
        method_to_patch = method_name or info_func.__name__

        @monkeypatch_method(cls, method_to_patch)
        def tracing_method(original, self, *args, **kwargs):
            entry_type, detail = info_func(self, *args, **kwargs)

            operation = entry_type
            if detail["name"] is not None:
                operation = operation + "/" + detail["name"]

            tr = TrackedRequest.instance()
            span = tr.start_span(operation=operation)

            for key in detail:
                span.tag(key, detail[key])

            try:
                return original(*args, **kwargs)
            finally:
                TrackedRequest.instance().stop_span()

        return tracing_method

    return decorator


def trace_function(func, info):
    try:

        def tracing_function(original, *args, **kwargs):
            if callable(info):
                entry_type, detail = info(*args, **kwargs)
            else:
                entry_type, detail = info

            operation = entry_type
            if detail["name"] is not None:
                operation = operation + "/" + detail["name"]

            tr = TrackedRequest.instance()
            span = tr.start_span(operation=operation)

            for key in detail:
                span.tag(key, detail[key])

            try:
                return original(*args, **kwargs)
            finally:
                TrackedRequest.instance().stop_span()

        return CallableProxy(func, tracing_function)
    except Exception:
        # If we can't wrap for any reason, just return the original
        return func
