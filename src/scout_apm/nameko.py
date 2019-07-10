# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from nameko.extensions import DependencyProvider
from nameko.web.handlers import HttpRequestHandler
from werkzeug.wrappers import Request

import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest


class ScoutReporter(DependencyProvider):
    def setup(self):
        scout_apm.core.install()

    def worker_setup(self, worker_ctx):
        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()

        # Get HTTP details for HTTP handlers
        if isinstance(worker_ctx.entrypoint, HttpRequestHandler):
            try:
                request = worker_ctx.args[0]
            except IndexError:
                pass
            else:
                if isinstance(request, Request):
                    tracked_request.tag("path", request.path)

        operation = (
            "Controller/"
            + worker_ctx.service.name
            + "."
            + worker_ctx.entrypoint.method_name
        )
        tracked_request.start_span(operation=operation)

    def worker_result(self, worker_ctx, result=None, exc_info=None):
        tracked_request = TrackedRequest.instance()
        if exc_info:
            tracked_request.tag("error", "true")
        tracked_request.stop_span()
