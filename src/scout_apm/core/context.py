# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.core.tracked_request import TrackedRequest

try:
    from asgiref.local import Local
except ImportError:
    from threading import local as Local


class LocalContext(object):
    def __init__(self):
        self._context = Local()

    def get_tracked_request(self):
        if not hasattr(self._context, "tracked_request"):
            self._context.tracked_request = TrackedRequest()
        return self._context.tracked_request

    def clear_tracked_request(self, instance):
        if getattr(self._context, "tracked_request", None) is instance:
            del self._context.tracked_request


context = LocalContext()
