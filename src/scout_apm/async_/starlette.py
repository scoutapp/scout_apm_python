# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from urllib.parse import parse_qsl

from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import create_filtered_path


def wrap_starlette_application(application):
    async def scout_wrapped_application(scope, receive, send):
        if scope["type"] != "http":
            await application(scope, receive, send)
            return

        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True
        operation = "Controller/Unknown"
        controller_span = tracked_request.start_span(operation=operation)

        tracked_request.tag(
            "path",
            create_filtered_path(scope["path"], parse_qsl(scope["query_string"])),
        )

        try:
            await application(scope, receive, send)
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

    return scout_wrapped_application
