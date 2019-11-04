# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from starlette.requests import Request

from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import create_filtered_path, ignore_path


class ScoutMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True
        operation = "Controller/Unknown"
        controller_span = tracked_request.start_span(operation=operation)

        tracked_request.tag(
            "path",
            create_filtered_path(request.url.path, request.query_params.multi_items()),
        )
        if ignore_path(request.url.path):
            tracked_request.tag("ignore_transaction", True)

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
            tracked_request.stop_span()
