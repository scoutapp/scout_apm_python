# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import scout_apm.core
from scout_apm.core.config import scout_config
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_request_queue_time,
)


def includeme(config):
    configs = {}
    pyramid_config = config.get_settings()
    for name in pyramid_config:
        if name.startswith("SCOUT_"):
            value = pyramid_config[name]
            clean_name = name.replace("SCOUT_", "").lower()
            configs[clean_name] = value
    scout_config.set(**configs)

    if scout_apm.core.install():
        config.add_tween("scout_apm.pyramid.instruments")


def instruments(handler, registry):
    def scout_tween(request):
        tracked_request = TrackedRequest.instance()

        with tracked_request.span(
            operation="Controller/Pyramid", should_capture_backtrace=False
        ) as span:
            path = request.path
            # mixed() returns values as *either* single items or lists
            url_params = [
                (k, v) for k, vs in request.GET.dict_of_lists().items() for v in vs
            ]
            tracked_request.tag("path", create_filtered_path(path, url_params))
            if ignore_path(path):
                tracked_request.tag("ignore_transaction", True)

            if scout_config.value("collect_remote_ip"):
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

            try:
                try:
                    response = handler(request)
                finally:
                    # Routing lives further down the call chain. So time it
                    # starting above, but only set the name if it gets a name
                    if request.matched_route is not None:
                        tracked_request.is_real_request = True
                        span.operation = "Controller/" + request.matched_route.name
            except Exception:
                tracked_request.tag("error", "true")
                raise

            if 500 <= response.status_code <= 599:
                tracked_request.tag("error", "true")

        return response

    return scout_tween
