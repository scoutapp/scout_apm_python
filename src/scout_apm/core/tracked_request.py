from __future__ import absolute_import

import logging
from datetime import datetime
from uuid import uuid4

from scout_apm.core.samplers import Samplers
from scout_apm.core.request_manager import RequestManager
from scout_apm.core.thread_local import ThreadLocalSingleton
from scout_apm.core.n_plus_one_call_set import NPlusOneCallSet
import scout_apm.core.backtrace

# Logging
logger = logging.getLogger(__name__)


class TrackedRequest(ThreadLocalSingleton):
    """
    This is a container which keeps track of all module instances for a single
    request. For convenience they are made available as attributes based on
    their keyname
    """
    def __init__(self, *args, **kwargs):
        self.req_id = 'req-' + str(uuid4())
        self.start_time = kwargs.get('start_time', datetime.utcnow())
        self.end_time = kwargs.get('end_time', None)
        self.active_spans = kwargs.get('active_spans', [])
        self.complete_spans = kwargs.get('complete_spans', [])
        self.tags = kwargs.get('tags', {})
        self.real_request = kwargs.get('real_request', False)
        self.callset = NPlusOneCallSet()
        logger.debug('Starting request: %s', self.req_id)

    def mark_real_request(self):
        self.real_request = True

    def is_real_request(self):
        return self.real_request

    def tag(self, key, value):
        if key in self.tags:
            logger.debug('Overwriting previously set tag for request %s: %s' % (self.req_id, key))
        self.tags[key] = value

    def start_span(self, *args, **kwargs):
        maybe_parent = self.current_span()

        if maybe_parent is not None:
            parent_id = maybe_parent.span_id
            if maybe_parent.ignore_children:
                kwargs['ignore'] = True
                kwargs['ignore_children'] = True
        else:
            parent_id = None

        kwargs['parent'] = parent_id
        kwargs['request_id'] = self.req_id

        new_span = Span(**kwargs)
        self.active_spans.append(new_span)
        return new_span

    def stop_span(self):
        stopping_span = None
        try:
            stopping_span = self.active_spans.pop()
        except IndexError as e:
            logger.debug('Exception when stopping span: %s' % repr(e))

        if stopping_span is not None:
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
        logger.debug('Stopping request: %s', self.req_id)
        if self.end_time is None:
            self.end_time = datetime.utcnow()
        RequestManager.instance().add_request(self)
        if self.is_real_request():
            Samplers.ensure_running()

        # This can fail if the Tracked Request was created directly, not through instance()
        try:
            self.release()
        except:
            pass


class Span:
    def __init__(self, *args, **kwargs):
        self.span_id = kwargs.get('span_id', 'span-' + str(uuid4()))
        self.start_time = kwargs.get('start_time', datetime.utcnow())
        self.end_time = kwargs.get('end_time', None)
        self.request_id = kwargs.get('request_id', None)
        self.operation = kwargs.get('operation', None)
        self.ignore = kwargs.get('ignore', False)
        self.ignore_children = kwargs.get('ignore_children', False)
        self.parent = kwargs.get('parent', None)
        self.tags = kwargs.get('tags', {})

    def stop(self):
        self.end_time = datetime.utcnow()

    def tag(self, key, value):
        if key in self.tags:
            logger.debug('Overwriting previously set tag for span %s: %s' % (self.span_id, key))
        self.tags[key] = value

    # In seconds
    def duration(self):
        if self.end_time is not None:
            return (self.end_time - self.start_time).total_seconds()
        else:
            # Current, running duration
            return (datetime.utcnow() - self.start_time).total_seconds()

    def duration_in_ms(self):
        return self.duration() / 1000

    # Add any interesting annotations to the span. Assumes that we are in the
    # process of stopping this span.
    def annotate(self):
        if self.operation is not None:
            if self.operation.startswith('Controller') or self.operation.startswith('Middleware'):
                return
        slow_threshold = 0.500
        if self.duration() > slow_threshold:
            self.capture_backtrace()

    def capture_backtrace(self):
        stack = scout_apm.core.backtrace.capture()
        self.tag('stack', stack)
