from __future__ import absolute_import

from collections import defaultdict

from apm.monkey import monkeypatch_method, CallableProxy
from apm.tracked_request import TrackedRequest

import time

from datetime import datetime
import re
import pdb

# The linter thinks the methods we monkeypatch are not used
# pylint: disable=W0612
def trace_method(cls, method_name=None):
    def decorator(info_func):
        method_to_patch = method_name or info_func.__name__

        @monkeypatch_method(cls, method_to_patch)
        def tracing_method(original, self, *args, **kwargs):
            entry_type, detail = info_func(self, *args, **kwargs)

            tr = TrackedRequest.instance()
            span = tr.start_span(operation=entry_type)

            for key in detail:
                span.note(key, detail[key])

            try:
                return original(*args, **kwargs)
            finally:
                TrackedRequest.instance().stop_span()
                print(span.dump())
        return tracing_method
    return decorator


def trace_function(func, info):
    try:
        def tracing_function(original, *args, **kwargs):
            if callable(info):
                entry_type, detail = info(*args, **kwargs)
            else:
                entry_type, detail = info

            span = TrackedRequest.instance().start_span(operation=entry_type)
            for key in detail:
                span.note(key, detail[key])

            try:
                return original(*args, **kwargs)
            finally:
                TrackedRequest.instance().stop_span()
                print(span.dump())

        return CallableProxy(func, tracing_function)
    except Exception:
        # If we can't wrap for any reason, just return the original
        return func

