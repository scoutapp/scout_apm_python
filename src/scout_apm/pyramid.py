# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import scout_apm.core
from scout_apm.core.config import ScoutConfig
from scout_apm.core.ignore import ignore_path
from scout_apm.core.queue_time import track_request_queue_time
from scout_apm.core.tracked_request import TrackedRequest


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
            if ignore_path(request.path):
                tracked_request.tag("ignore_transaction", True)

            tracked_request.tag("path", request.path)

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

            try:
                queue_time = request.headers.get(
                    "x-queue-start", default=""
                ) or request.headers.get("x-request-start", default="")
            except Exception:
                pass
            else:
                track_request_queue_time(queue_time, tracked_request)

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
