# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import wrapt
from urllib.parse import parse_qsl

from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import create_filtered_path, ignore_path


@wrapt.decorator
async def wrapped_http_request(wrapped, instance, args, kwargs):
    message = _extract_message(*args, **kwargs)
    scope = instance.scope

    if message.get("more_body"):
        # handle() won't be called yet
        return await wrapped(instance, *args, **kwargs)

    tracked_request = TrackedRequest.instance()
    tracked_request.is_real_request = True

    path = scope.get("root_path", "") + scope["path"]
    query_params = parse_qsl(scope.get("query_string", b"").decode('utf-8'))
    tracked_request.tag("path", create_filtered_path(path, query_params))
    if ignore_path(path):
        tracked_request.tag("ignore_transaction", True)

    # We only care about the last values of headers so don't care that we use
    # a plain dict rather than a multi-value dict
    headers = {k.lower(): v for k, v in scope.get("headers", ())}

    user_ip = (
        headers.get(b"x-forwarded-for", b"").decode('latin1').split(",")[0]
        or headers.get(b"client-ip", b"").decode('latin1').split(",")[0]
        or scope.get("client", ("",))[0]
    )
    tracked_request.tag("user_ip", user_ip)

    tracked_request.start_span(
        operation="Controller/{}.{}".format(
            instance.__module__, instance.__class__.__qualname__
        )
    )

    try:
        return await wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()


def _extract_message(message, *args, **kwargs):
    return message
