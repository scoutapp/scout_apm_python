# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import wrapt

from scout_apm.core.tracked_request import TrackedRequest


def trace_method(cls, method_name=None):
    def decorator(info_func):
        method_to_patch = method_name or info_func.__name__

        @wrapt.decorator
        def wrapper(wrapped, instance, args, kwargs):
            entry_type, detail = info_func(instance, *args, **kwargs)
            operation = entry_type
            if detail["name"] is not None:
                operation = operation + "/" + detail["name"]

            tracked_request = TrackedRequest.instance()
            span = tracked_request.start_span(operation=operation)
            for key, value in detail.items():
                span.tag(key, value)

            try:
                return wrapped(*args, **kwargs)
            finally:
                tracked_request.stop_span()

        setattr(cls, method_to_patch, wrapper(getattr(cls, method_to_patch)))

        return wrapper

    return decorator


def trace_function(func, info):
    try:

        @wrapt.decorator
        def wrapper(wrapped, instance, args, kwargs):
            if callable(info):
                entry_type, detail = info(*args, **kwargs)
            else:
                entry_type, detail = info

            operation = entry_type
            if detail["name"] is not None:
                operation = operation + "/" + detail["name"]

            tracked_request = TrackedRequest.instance()
            span = tracked_request.start_span(operation=operation)
            for key in detail:
                span.tag(key, detail[key])

            try:
                return wrapped(*args, **kwargs)
            finally:
                tracked_request.stop_span()

        return wrapper(func)
    except Exception:
        # If we can't wrap for any reason, just return the original
        return func
