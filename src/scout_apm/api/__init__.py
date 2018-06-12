from scout_apm.core.tracked_request import TrackedRequest

import sys
import logging


# Logging
logger = logging.getLogger(__name__)


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


class instrument(ContextDecorator):
    def __init__(self, operation, kind='Custom', tags={}):
        self.operation = kind + '/' + operation
        self.tags = tags

    def __enter__(self):
        tr = TrackedRequest.instance()
        self.span = tr.start_span(operation=self.operation)
        for key, value in self.tags.items():
            self.tag(key, value)
        return self

    def __exit__(self, *exc):
        tr = TrackedRequest.instance()
        tr.stop_span()
        return False

    def tag(self, key, value):
        if self.span is not None:
            self.span.tag(key, value)

