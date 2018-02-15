"""
Represents a single whole request.
"""

import logging
import threading
from datetime import datetime
from uuid import uuid4

from scout_apm.context import agent_context

from .commands import (FinishRequest, StartRequest, StartSpan, StopSpan,
                       TagRequest, TagSpan)

# Logging
logger = logging.getLogger(__name__)


class ThreadLocalSingleton(object):
    def __init__(self):
        if not hasattr(self.__class__, '_thread_lookup'):
            self.__class__._thread_lookup = threading.local()
        self.__class__._thread_lookup.instance = self

    def release(self):
        if getattr(self.__class__._thread_lookup, 'instance', None) is self:
            self.__class__._thread_lookup.instance = None


class TrackedRequest(ThreadLocalSingleton):
    """
    This is a container which keeps track of all module instances for a single
    request. For convenience they are made available as attributes based on
    their keyname
    """
    def __init__(self):
        super(TrackedRequest, self).__init__()
        self.req_id = 'req-' + str(uuid4())
        self.spans = []
        self.socket = agent_context.socket
        self.socket.open()
        logger.info('Starting request:', self.req_id)
        self.send_start_request()

    def send_start_request(self):
        self.socket.send(StartRequest(self.req_id))

    def send_finish_request(self):
        self.socket.send(FinishRequest(self.req_id))

    def tag(self, key, value):
        self.socket.send(TagRequest(self.request_id, key, value))

    def start_span(self, operation=None):
        maybe_parent = self.current_span()

        if maybe_parent is not None:
            parent_id = maybe_parent.span_id
        else:
            parent_id = None

        new_span = Span(
            self.socket,
            request_id=self.req_id,
            operation=operation,
            parent=parent_id)
        self.spans.append(new_span)
        return new_span

    def stop_span(self):
        stopping_span = self.spans.pop()
        stopping_span.stop()
        if len(self.spans) == 0:
            self.finish()

    def current_span(self):
        if len(self.spans) > 0:
            return self.spans[-1]
        else:
            return None

    # Request is done, release any info we have about it.
    def finish(self):
        logger.info('Stopping request:', self.req_id)
        self.send_finish_request()
        self.socket.close()
        self.release()

    # XXX: TrackedRequest knows too much about threads & making itself
    # Move this whole method somewhere else ( a RequestManager obj? )
    @classmethod
    def instance(cls):
        if hasattr(cls, '_thread_lookup'):
            if getattr(cls._thread_lookup, 'instance', None) is not None:
                return getattr(cls._thread_lookup, 'instance', None)
            return TrackedRequest()
        return TrackedRequest()


class Span:
    def __init__(self, socket, request_id=None, operation=None, parent=None):
        self.span_id = 'span-' + str(uuid4())
        self.request_id = request_id
        self.operation = operation
        self.parent = parent
        self.start_time = datetime.now()
        self.end_time = None
        self.socket = socket

        self.send_start_span()

    def send_start_span(self):
        if self.request_id is None:
            return

        self.socket.send(StartSpan(
            self.request_id,
            self.span_id,
            self.parent,
            self.operation
        ))

    def send_stop_span(self):
        self.socket.send(StopSpan(self.request_id, self.span_id))

    def dump(self):
        if self.end_time is None:
            logger.info(self.operation)
        return 'request=%s operation=%s id=%s parent=%s start_time=%s end_time=%s' % (
                self.request_id,
                self.operation,
                self.span_id,
                self.parent,
                self.start_time.isoformat(),
                self.end_time.isoformat()
            )

    def stop(self):
        self.end_time = datetime.now()
        self.send_stop_span()

    def tag(self, key, value):
        self.socket.send(TagSpan(self.request_id, self.span_id, key, value))

    # In seconds
    def duration(self):
        if self.end_time is not None:
            (self.end_time - self.start_time).total_seconds()
        else:
            # Current, running duration
            (datetime.now() - self.start_time).total_seconds()
