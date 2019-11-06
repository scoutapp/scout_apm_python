# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import wrapt
from bottle import request

import scout_apm.core
from scout_apm.core.config import scout_config
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_amazon_request_queue_time,
    track_request_queue_time,
)


class ScoutPlugin(object):
    def __init__(self):
        self.name = "scout"
        self.api = 2

    def set_config_from_bottle(self, app):
        bottle_configs = {}
        for key in scout_config.known_keys():
            value = app.config.get("scout.{}".format(key))
            if value is not None and value != "":
                bottle_configs[key] = value
        scout_config.set(**bottle_configs)

    def setup(self, app):
        self.set_config_from_bottle(app)
        installed = scout_apm.core.install()
        self._do_nothing = not installed

    def apply(self, callback, context):
        if self._do_nothing:
            return callback
        return wrap_callback(callback)


@wrapt.decorator
def wrap_callback(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    tracked_request.is_real_request = True

    path = request.path
    # allitems() is an undocumented bottle internal
    tracked_request.tag("path", create_filtered_path(path, request.query.allitems()))
    if ignore_path(path):
        tracked_request.tag("ignore_transaction", True)

    if request.route.name is not None:
        controller_name = request.route.name
    else:
        controller_name = request.route.rule
    if controller_name == "/":
        controller_name = "/home"
    if not controller_name.startswith("/"):
        controller_name = "/" + controller_name
    tracked_request.start_span(
        operation="Controller{}".format(controller_name), should_capture_backtrace=False
    )

    # Determine a remote IP to associate with the request. The
    # value is spoofable by the requester so this is not suitable
    # to use in any security sensitive context.
    user_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0]
        or request.headers.get("client-ip", "").split(",")[0]
        or request.environ.get("REMOTE_ADDR")
    )
    tracked_request.tag("user_ip", user_ip)

    tracked_queue_time = False
    queue_time = request.headers.get("x-queue-start", "") or request.headers.get(
        "x-request-start", ""
    )
    tracked_queue_time = track_request_queue_time(queue_time, tracked_request)
    if not tracked_queue_time:
        amazon_queue_time = request.headers.get("x-amzn-trace-id", "")
        track_amazon_request_queue_time(amazon_queue_time, tracked_request)

    try:
        return wrapped(*args, **kwargs)
    except Exception:
        tracked_request.tag("error", "true")
        raise
    finally:
        tracked_request.stop_span()
