# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import scout_apm.core
from scout_apm.compat import ContextDecorator, text
from scout_apm.core.config import ScoutConfig
from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)


__all__ = [
    "BackgroundTransaction",
    "Config",
    "Context",
    "WebTransaction",
    "install",
    "instrument",
]


class Context(object):
    @classmethod
    def add(self, key, value):
        """Adds context to the currently executing request.

        :key: Any String identifying the request context.
              Example: "user_ip", "plan", "alert_count"
        :value: Any json-serializable type.
              Example: "1.1.1.1", "free", 100
        :returns: nothing.
        """
        TrackedRequest.instance().tag(key, value)


class Config(ScoutConfig):
    pass


def install(*args, **kwargs):
    scout_apm.core.install(*args, **kwargs)


def ignore_transaction():
    TrackedRequest.instance().tag("ignore_transaction", True)


class instrument(ContextDecorator):
    def __init__(self, operation, kind="Custom", tags={}):
        self.operation = text(kind) + "/" + text(operation)
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
        self.name = text(name)
        self.tags = tags

    @classmethod
    def start(cls, kind, name, tags={}):
        operation = text(kind) + "/" + text(name)

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
        Transaction.start("Controller", text(name), tags)

    def __enter__(self):
        Transaction.start("Controller", self.name, self.tags)


class BackgroundTransaction(Transaction):
    @classmethod
    def start(cls, name, tags={}):
        Transaction.start("Job", text(name), tags)

    def __enter__(self):
        Transaction.start("Job", self.name, self.tags)
