# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from nameko.extensions import DependencyProvider
from nameko.web.handlers import HttpRequestHandler
from werkzeug.wrappers import Request

import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.queue_time import track_request_queue_time


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

                # Determine a remote IP to associate with the request. The value is
                # spoofable by the requester so this is not suitable to use in any
                # security sensitive context.
                user_ip = (
                    request.headers.get("x-forwarded-for", default="").split(",")[0]
                    or request.headers.get("client-ip", default="").split(",")[0]
                    or request.remote_addr
                )
                tracked_request.tag("user_ip", user_ip)

                queue_time = request.headers.get(
                    "x-queue-start", default=""
                ) or request.headers.get("x-request-start", default="")
                track_request_queue_time(queue_time, tracked_request)

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
