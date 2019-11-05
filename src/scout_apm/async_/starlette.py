# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from starlette.requests import Request

from scout_apm.core.config import scout_config
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_amazon_request_queue_time,
    track_request_queue_time,
)


class ScoutMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scout_config.value("monitor"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        tracked_request = TrackedRequest.instance()
        # Can't name controller until post-routing - see final clause
        controller_span = tracked_request.start_span(operation="Controller/Unknown")

        tracked_request.tag(
            "path",
            create_filtered_path(request.url.path, request.query_params.multi_items()),
        )
        if ignore_path(request.url.path):
            tracked_request.tag("ignore_transaction", True)

        user_ip = (
            request.headers.get("x-forwarded-for", default="").split(",")[0]
            or request.headers.get("client-ip", default="").split(",")[0]
            or request.client.host
        )
        tracked_request.tag("user_ip", user_ip)

        queue_time = request.headers.get(
            "x-queue-start", default=""
        ) or request.headers.get("x-request-start", default="")
        tracked_queue_time = track_request_queue_time(queue_time, tracked_request)
        if not tracked_queue_time:
            amazon_queue_time = request.headers.get("x-amzn-trace-id", default="")
            track_amazon_request_queue_time(amazon_queue_time, tracked_request)

        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            tracked_request.tag("error", "true")
            raise exc
        finally:
            if "endpoint" in scope:
                endpoint = scope["endpoint"]
                controller_span.operation = "Controller/{}.{}".format(
                    endpoint.__module__, endpoint.__qualname__
                )
                tracked_request.is_real_request = True
            tracked_request.stop_span()
