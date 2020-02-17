# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import scout_apm.core
from scout_apm.compat import ContextDecorator, text
from scout_apm.core.config import ScoutConfig
from scout_apm.core.tracked_request import TrackedRequest

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


install = scout_apm.core.install


def ignore_transaction():
    TrackedRequest.instance().tag("ignore_transaction", True)


class instrument(ContextDecorator):
    def __init__(self, operation, kind="Custom", tags=None):
        self.operation = text(kind) + "/" + text(operation)
        if tags is None:
            self.tags = {}
        else:
            self.tags = tags

    def __enter__(self):
        tracked_request = TrackedRequest.instance()
        self.span = tracked_request.start_span(operation=self.operation)
        for key, value in self.tags.items():
            self.tag(key, value)
        return self

    def __exit__(self, *exc):
        tracked_request = TrackedRequest.instance()
        tracked_request.stop_span()
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

    def __init__(self, name, tags=None):
        self.name = text(name)
        if tags is None:
            self.tags = {}
        else:
            self.tags = tags

    @classmethod
    def start(cls, kind, name, tags=None):
        operation = text(kind) + "/" + text(name)

        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True
        span = tracked_request.start_span(
            operation=operation, should_capture_backtrace=False
        )
        if tags is not None:
            for key, value in tags.items():
                tracked_request.tag(key, value)
        return span

    @classmethod
    def stop(cls):
        tracked_request = TrackedRequest.instance()
        tracked_request.stop_span()
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
    def start(cls, name, tags=None):
        super(WebTransaction, cls).start("Controller", text(name), tags)

    def __enter__(self):
        super(WebTransaction, self).start("Controller", self.name, self.tags)


class BackgroundTransaction(Transaction):
    @classmethod
    def start(cls, name, tags=None):
        super(BackgroundTransaction, cls).start("Job", text(name), tags)

    def __enter__(self):
        super(BackgroundTransaction, self).start("Job", self.name, self.tags)


def rename_transaction(name):
    if name is not None:
        tracked_request = TrackedRequest.instance()
        tracked_request.tag("transaction.name", name)
