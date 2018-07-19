import scout_apm.core
from scout_apm.core.config import ScoutConfig
from scout_apm.api.context import Context as ScoutContext
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


class Context(ScoutContext):
    pass


class Config(ScoutConfig):
    pass


def install(*args, **kwargs):
    scout_apm.core.install(*args, **kwargs)


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


class Transaction(ContextDecorator):
    """
    This Class is not meant to be used directly.
    Use one of the subclasses
    (WebTransaction or BackgroundTransaction)
    """

    def __init__(self, name, tags={}):
        self.name = name
        self.tags = tags

    @classmethod
    def start(cls, kind, name, tags={}):
        operation = kind + '/' + name

        tr = TrackedRequest.instance()
        tr.mark_real_request()
        span = tr.start_span(operation=operation)
        for key, value in tags.items():
            tr.tag(key, value)
        return span

    @classmethod
    def stop(cls):
        tr = TrackedRequest.instance()
        tr.stop_span()
        return True


    # __enter__ must be defined by child classes.


    # *exc is any exception raised. Ignore that
    def __exit__(self, *exc):
        WebTransaction.stop()
        return False

    def tag(self, key, value):
        if self.span is not None:
            self.span.tag(key, value)


class WebTransaction(Transaction):
    @classmethod
    def start(cls, name, tags={}):
        Transaction.start("Controller", name, tags)

    def __enter__(self):
        Transaction.start("Controller", self.name, self.tags)


class BackgroundTransaction(Transaction):
    @classmethod
    def start(cls, name, tags={}):
        Transaction.start("Job", name, tags)

    def __enter__(self):
        Transaction.start("Job", self.name, self.tags)
