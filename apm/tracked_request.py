"""
Represents a single whole request.

Can be marked with notes
"""

from uuid import uuid4
from datetime import datetime
import threading
import pdb


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
    This is a container which keeps track of all module instances for a single request. For convenience they are made
    available as attributes based on their keyname
    """
    def __init__(self):
        super(TrackedRequest, self).__init__()
        self.id = "req-" + str(uuid4())
        self.notes = dict()
        self.spans = []

    def note(self, key, value):
        self.notes[key] = value

    def start_span(self, operation=None):
        maybe_parent = self.current_span()
        if maybe_parent is not None:
            parent_id = maybe_parent.id
        else:
            parent_id = None

        new_span = Span(request=self.id, operation=operation, parent=parent_id)
        self.spans.append(new_span)
        return new_span

    def stop_span(self):
        stopping_span = self.spans.pop()
        stopping_span.stop()
        if len(self.spans) == 0:
            self.release()

    def current_span(self):
        if len(self.spans) > 0:
            return self.spans[-1]
        else:
            return None

    # XXX: TrackedRequest knows too much about threads & making itself
    # Move this whole method somewhere else ( a RequestManager obj? )
    @classmethod
    def instance(cls):
        if hasattr(cls, '_thread_lookup'):
            if getattr(cls._thread_lookup, 'instance', None) is not None:
                return getattr(cls._thread_lookup, 'instance', None)
            else:
                return TrackedRequest()
        else:
            return TrackedRequest()

class Span:
    def __init__(self, request=None, operation=None, parent=None):
        self.id = "span-" + str(uuid4())
        self.request = request
        self.operation = operation
        self.parent = parent
        self.notes = dict()
        self.start_time = datetime.now()
        self.end_time = None

    def dump(self):
        if self.end_time is None:
            print(self.operation)
        return "request=%s operation=%s id=%s parent=%s notes=%s start_time=%s end_time=%s" % (
                self.request,
                self.operation,
                self.id,
                self.parent,
                self.notes,
                self.start_time.isoformat(),
                self.end_time.isoformat()
            )

    def stop(self):
        self.end_time = datetime.now()

    # In seconds
    def duration(self):
        if self.end_time is not None:
            (self.end_time - self.start_time).total_seconds()
        else:
            # Current, running duration
            (datetime.now() - self.start_time).total_seconds()

    def note(self, key, value):
        self.notes[key] = value

