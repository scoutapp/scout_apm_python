# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from nameko.extensions import DependencyProvider
from nameko.web.handlers import HttpRequestHandler
from werkzeug.wrappers import Request

import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import werkzeug_track_request_data


class ScoutReporter(DependencyProvider):
    def setup(self):
        installed = scout_apm.core.install()
        self._do_nothing = not installed

    def worker_setup(self, worker_ctx):
        if self._do_nothing:
            return
        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True

        # Get HTTP details for HTTP handlers
        if isinstance(worker_ctx.entrypoint, HttpRequestHandler):
            try:
                request = worker_ctx.args[0]
            except IndexError:
                pass
            else:
                self._track_request_data(request, tracked_request)

        operation = (
            "Controller/"
            + worker_ctx.service.name
            + "."
            + worker_ctx.entrypoint.method_name
        )
        tracked_request.start_span(operation=operation, should_capture_backtrace=False)

    def _track_request_data(self, request, tracked_request):
        if not isinstance(request, Request):
            return

        werkzeug_track_request_data(request, tracked_request)

    def worker_result(self, worker_ctx, result=None, exc_info=None):
        if self._do_nothing:
            return
        tracked_request = TrackedRequest.instance()
        if exc_info:
            tracked_request.tag("error", "true")
        tracked_request.stop_span()
