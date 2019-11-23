# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from nameko.extensions import DependencyProvider
from nameko.web.handlers import HttpRequestHandler
from werkzeug.wrappers import Request, Response

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
                if isinstance(request, Request):
                    werkzeug_track_request_data(request, tracked_request)

        operation = (
            "Controller/"
            + worker_ctx.service.name
            + "."
            + worker_ctx.entrypoint.method_name
        )
        tracked_request.start_span(operation=operation, should_capture_backtrace=False)

    def worker_result(self, worker_ctx, result=None, exc_info=None):
        if self._do_nothing:
            return
        tracked_request = TrackedRequest.instance()

        if exc_info:
            tracked_request.tag("error", "true")
        elif isinstance(worker_ctx.entrypoint, HttpRequestHandler):
            # Handle the cases that HttpRequestHandler.response_from_result
            # does
            if isinstance(result, Response):
                status_code = result.status_code
            elif isinstance(result, tuple):
                if len(result) == 3:
                    status_code, _headers, _payload = result
                elif len(result) == 2:
                    status_code, _payload = result
                else:
                    # Nameko doesn't support other formats, so we know it will
                    # turn this into an error
                    status_code = 500
            else:
                status_code = 200

            if 500 <= status_code <= 599:
                tracked_request.tag("error", "true")

        tracked_request.stop_span()
