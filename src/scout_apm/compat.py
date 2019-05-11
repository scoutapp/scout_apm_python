# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

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

__all__ = ["ContextDecorator", "queue", "string_type", "text_type"]
