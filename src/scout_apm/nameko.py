# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from nameko.extensions import DependencyProvider

from scout_apm.core.tracked_request import TrackedRequest


class ScoutReporter(DependencyProvider):
    def worker_setup(self, worker_ctx):
        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()
        tracked_request.start_span(operation="Test")

    def worker_result(self, worker_ctx, result=None, exc_info=None):
        TrackedRequest.instance().stop_span()
