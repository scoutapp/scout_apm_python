# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import threading

from scout_apm.core.tracked_request import TrackedRequest


class ThreadLocalContext(object):
    def __init__(self):
        self._context = threading.local()

    def get_tracked_request(self):
        if not hasattr(self._context, "tracked_request"):
            self._context.tracked_request = TrackedRequest()
        return self._context.tracked_request

    def clear_tracked_request(self, instance):
        if getattr(self._context, "tracked_request", None) is instance:
            del self._context.tracked_request


context = ThreadLocalContext()
