from urllib.parse import parse_qsl

from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import create_filtered_path


def wrap_asgi_application(application):
    async def scout_wrapped_application(scope, receive, send):
        if scope["type"] != "http":
            await application(scope, receive, send)
            return

        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()
        operation = "Controller/" + scope["method"] + "_" + scope["path"]
        tracked_request.start_span(operation=operation)

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
            tracked_request.stop_span()

    return scout_wrapped_application
