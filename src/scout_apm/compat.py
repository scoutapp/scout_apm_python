# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import sys

string_type = str if sys.version_info[0] >= 3 else basestring  # noqa: F821
text_type = str if sys.version_info[0] >= 3 else unicode  # noqa: F821

# Python 2 (and very early 3.x) didn't have ContextDecorator, so define it for ourselves
if sys.version_info < (3, 2):
    import functools

    class ContextDecorator(object):
        def __call__(self, f):
            @functools.wraps(f)
            def decorated(*args, **kwds):
                with self:
                    return f(*args, **kwds)

            return decorated


else:
    from contextlib import ContextDecorator

try:
    # Python 3.x
    import queue
except ImportError:
    # Python 2.x
    import Queue as queue

# datetime_to_timestamp converts a naive UTC datetime to a unix timestamp
if sys.version_info >= (3, 3):

    def datetime_to_timestamp(datetime_obj):
        return datetime_obj.replace(tzinfo=dt.timezone.utc).timestamp()


else:
    _EPOCH = dt.datetime(1970, 1, 1)

    def datetime_to_timestamp(datetime_obj):
        return (datetime_obj - _EPOCH).total_seconds()


def text(value, encoding="utf-8", errors="strict"):
    """
    Convert a value to str on Python 3 and unicode on Python 2.
    """
    if isinstance(value, text_type):
        return value
    elif isinstance(value, bytes):
        return text_type(value, encoding, errors)
    else:
        return text_type(value)


__all__ = [
    "ContextDecorator",
    "datetime_to_timestamp",
    "queue",
    "string_type",
    "text",
    "text_type",
]
