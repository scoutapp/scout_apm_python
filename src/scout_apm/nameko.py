# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from nameko.extensions import DependencyProvider
from nameko.web.handlers import HttpRequestHandler
from werkzeug.wrappers import Request

import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_amazon_request_queue_time,
    track_request_queue_time,
)


class ScoutReporter(DependencyProvider):
    def setup(self):
        installed = scout_apm.core.install()
        self._do_nothing = not installed

    def worker_setup(self, worker_ctx):
        if self._do_nothing:
            return
        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()

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
        tracked_request.start_span(operation=operation)

    def _track_request_data(self, request, tracked_request):
        if not isinstance(request, Request):
            return

        path = request.path
        tracked_request.tag(
            "path", create_filtered_path(path, request.args.items(multi=True))
        )
        if ignore_path(path):
            tracked_request.tag("ignore_transaction", True)

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
        tracked_queue_time = track_request_queue_time(queue_time, tracked_request)
        if not tracked_queue_time:
            amazon_queue_time = request.headers.get("x-amzn-trace-id", default="")
            track_amazon_request_queue_time(amazon_queue_time, tracked_request)

    def worker_result(self, worker_ctx, result=None, exc_info=None):
        if self._do_nothing:
            return
        tracked_request = TrackedRequest.instance()
        if exc_info:
            tracked_request.tag("error", "true")
        tracked_request.stop_span()
