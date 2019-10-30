# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import logging
from uuid import uuid4

from scout_apm.core import backtrace, objtrace
from scout_apm.core.commands import BatchCommand
from scout_apm.core.n_plus_one_call_set import NPlusOneCallSet
from scout_apm.core.samplers.memory import get_rss_in_mb
from scout_apm.core.samplers.thread import SamplersThread
from scout_apm.core.socket import CoreAgentSocket

logger = logging.getLogger(__name__)


class TrackedRequest(object):
    """
    This is a container which keeps track of all module instances for a single
    request. For convenience they are made available as attributes based on
    their keyname
    """

    __slots__ = (
        "request_id",
        "start_time",
        "end_time",
        "active_spans",
        "complete_spans",
        "tags",
        "is_real_request",
        "_memory_start",
        "callset",
    )

    @classmethod
    def instance(cls):
        from scout_apm.core.context import context

        return context.get_tracked_request()

    def __init__(self):
        self.request_id = "req-" + str(uuid4())
        self.start_time = dt.datetime.utcnow()
        self.end_time = None
        self.active_spans = []
        self.complete_spans = []
        self.tags = {}
        self.is_real_request = False
        self._memory_start = get_rss_in_mb()
        self.callset = NPlusOneCallSet()
        logger.debug("Starting request: %s", self.request_id)

    def __repr__(self):
        # Incomplete to avoid TMI
        return "<TrackedRequest(request_id={}, tags={})>".format(
            repr(self.request_id), repr(self.tags)
        )

    def tag(self, key, value):
        if key in self.tags:
            logger.debug(
                "Overwriting previously set tag for request %s: %s",
                self.request_id,
                key,
            )
        self.tags[key] = value

    def start_span(self, *args, **kwargs):
        maybe_parent = self.current_span()

        if maybe_parent is not None:
            parent_id = maybe_parent.span_id
            if maybe_parent.ignore_children:
                kwargs["ignore"] = True
                kwargs["ignore_children"] = True
        else:
            parent_id = None

        kwargs["parent"] = parent_id
        kwargs["request_id"] = self.request_id

        new_span = Span(**kwargs)
        self.active_spans.append(new_span)
        return new_span

    def stop_span(self):
        try:
            stopping_span = self.active_spans.pop()
        except IndexError as e:
            logger.debug("Exception when stopping span: %r", e)
        else:
            stopping_span.stop()
            if not stopping_span.ignore:
                stopping_span.annotate()
                self.complete_spans.append(stopping_span)

        if len(self.active_spans) == 0:
            self.finish()

    def current_span(self):
        if len(self.active_spans) > 0:
            return self.active_spans[-1]
        else:
            return None

    # Request is done, release any info we have about it.
    def finish(self):
        logger.debug("Stopping request: %s", self.request_id)
        if self.end_time is None:
            self.end_time = dt.datetime.utcnow()
        if self.is_real_request:
            self.tag("mem_delta", self._get_mem_delta())
            if not self.is_ignored():
                batch_command = BatchCommand.from_tracked_request(self)
                CoreAgentSocket.instance().send(batch_command)
            SamplersThread.ensure_started()

        from scout_apm.core.context import context

        context.clear_tracked_request(self)

    def _get_mem_delta(self):
        current_mem = get_rss_in_mb()
        if current_mem > self._memory_start:
            return current_mem - self._memory_start
        return 0.0

    # A request is ignored if the tag "ignore_transaction" is set to True
    def is_ignored(self):
        return self.tags.get("ignore_transaction", False)


class Span(object):
    __slots__ = (
        "span_id",
        "start_time",
        "end_time",
        "request_id",
        "operation",
        "ignore",
        "ignore_children",
        "parent",
        "tags",
        "start_objtrace_counts",
        "end_objtrace_counts",
        "should_capture_backtrace",
    )

    def __init__(
        self,
        request_id=None,
        operation=None,
        ignore=False,
        ignore_children=False,
        parent=None,
        should_capture_backtrace=True,
    ):
        self.span_id = "span-" + str(uuid4())
        self.start_time = dt.datetime.utcnow()
        self.end_time = None
        self.request_id = request_id
        self.operation = operation
        self.ignore = ignore
        self.ignore_children = ignore_children
        self.parent = parent
        self.tags = {}
        self.start_objtrace_counts = objtrace.get_counts()
        self.end_objtrace_counts = (0, 0, 0, 0)
        self.should_capture_backtrace = should_capture_backtrace

    def __repr__(self):
        # Incomplete to avoid TMI
        return "<Span(span_id={}, operation={}, ignore={}, tags={})>".format(
            repr(self.span_id), repr(self.operation), repr(self.ignore), repr(self.tags)
        )

    def stop(self):
        self.end_time = dt.datetime.utcnow()
        self.end_objtrace_counts = objtrace.get_counts()

    def tag(self, key, value):
        if key in self.tags:
            logger.debug(
                "Overwriting previously set tag for span %s: %s", self.span_id, key
            )
        self.tags[key] = value

    # In seconds
    def duration(self):
        if self.end_time is not None:
            return (self.end_time - self.start_time).total_seconds()
        else:
            # Current, running duration
            return (dt.datetime.utcnow() - self.start_time).total_seconds()

    # Add any interesting annotations to the span. Assumes that we are in the
    # process of stopping this span.
    def annotate(self):
        self.add_allocation_tags()
        if not self.should_capture_backtrace:
            return
        slow_threshold = 0.5
        if self.duration() > slow_threshold:
            self.capture_backtrace()

    def add_allocation_tags(self):
        if not objtrace.is_extension:
            return

        start_allocs = (
            self.start_objtrace_counts[0]
            + self.start_objtrace_counts[1]
            + self.start_objtrace_counts[2]
        )
        end_allocs = (
            self.end_objtrace_counts[0]
            + self.end_objtrace_counts[1]
            + self.end_objtrace_counts[2]
        )

        # If even one of the counters rolled over, we're pretty much
        # guaranteed to have end_allocs be less than start_allocs.
        # This should rarely happen. Max Unsigned Long Long is a big number
        if end_allocs - start_allocs < 0:
            logger.debug(
                "End allocation count smaller than start allocation "
                "count for span %s: start = %d, end = %d",
                self.span_id,
                start_allocs,
                end_allocs,
            )
            return 0

        self.tag("allocations", end_allocs - start_allocs)
        self.tag("start_allocations", start_allocs)
        self.tag("stop_allocations", end_allocs)

    def capture_backtrace(self):
        self.tag("stack", backtrace.capture())
