# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import scout_apm.core
from scout_apm.core.config import ScoutConfig
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_amazon_request_queue_time,
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
    ScoutConfig.set(**configs)

    if scout_apm.core.install():
        config.add_tween("scout_apm.pyramid.instruments")


def instruments(handler, registry):
    def scout_tween(request):
        tracked_request = TrackedRequest.instance()
        span = tracked_request.start_span(operation="Controller/Pyramid")

        try:
            path = request.path
            # mixed() returns values as *either* single items or lists
            url_params = [
                (k, v) for k, vs in request.GET.dict_of_lists().items() for v in vs
            ]
            tracked_request.tag("path", create_filtered_path(path, url_params))
            if ignore_path(path):
                tracked_request.tag("ignore_transaction", True)

            try:
                # Determine a remote IP to associate with the request. The value is
                # spoofable by the requester so this is not suitable to use in any
                # security sensitive context.
                user_ip = (
                    request.headers.get("x-forwarded-for", default="").split(",")[0]
                    or request.headers.get("client-ip", default="").split(",")[0]
                    or request.remote_addr
                )
            except Exception:
                pass
            else:
                tracked_request.tag("user_ip", user_ip)

            tracked_queue_time = False
            try:
                queue_time = request.headers.get(
                    "x-queue-start", default=""
                ) or request.headers.get("x-request-start", default="")
            except Exception:
                pass
            else:
                tracked_queue_time = track_request_queue_time(
                    queue_time, tracked_request
                )
            if not tracked_queue_time:
                try:
                    amazon_queue_time = request.headers.get(
                        "x-amzn-trace-id", default=""
                    )
                except Exception:
                    pass
                else:
                    track_amazon_request_queue_time(amazon_queue_time, tracked_request)

            try:
                response = handler(request)
            except Exception:
                tracked_request.tag("error", "true")
                raise

            # This happens further down the call chain. So time it starting
            # above, but only name it if it gets to here.
            if request.matched_route is not None:
                tracked_request.mark_real_request()
                span.operation = "Controller/" + request.matched_route.name

        finally:
            tracked_request.stop_span()

        return response

    return scout_tween
