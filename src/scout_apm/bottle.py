# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from bottle import request

import scout_apm.core
from scout_apm.core.config import ScoutConfig
from scout_apm.core.context import AgentContext
from scout_apm.core.ignore import ignore_path
from scout_apm.core.queue_time import track_request_queue_time
from scout_apm.core.tracked_request import TrackedRequest


class ScoutPlugin(object):
    def __init__(self):
        self.name = "scout"
        self.api = 2

    def set_config_from_bottle(self, app):
        scout_config = ScoutConfig()
        bottle_configs = {}
        for k in scout_config.known_keys():
            value = app.config.get("scout.{}".format(k))
            if value is not None and value != "":
                bottle_configs[k] = value
        scout_config.set(**bottle_configs)
        return scout_config

    def setup(self, app):
        self.set_config_from_bottle(app)
        scout_apm.core.install()

    def apply(self, callback, context):
        if not AgentContext.instance.config.value("monitor"):
            return callback

        def wrapper(*args, **kwargs):
            tracked_request = TrackedRequest.instance()
            tracked_request.mark_real_request()

            if request.route.name is not None:
                path = request.route.name
            else:
                path = request.route.rule
            if path == "/":
                path = "/home"
            if not path.startswith("/"):
                path = "/{}".format(path)

            tracked_request.tag("path", path)
            if ignore_path(path):
                tracked_request.tag("ignore_transaction", True)

            tracked_request.start_span(operation="Controller{}".format(path))

            try:
                # Determine a remote IP to associate with the request. The
                # value is spoofable by the requester so this is not suitable
                # to use in any security sensitive context.
                user_ip = (
                    request.headers.get("x-forwarded-for", "").split(",")[0]
                    or request.headers.get("client-ip", "").split(",")[0]
                    or request.environ.get("REMOTE_ADDR")
                )
            except Exception:
                pass
            else:
                tracked_request.tag("user_ip", user_ip)

            try:
                queue_time = request.headers.get(
                    "x-queue-start", ""
                ) or request.headers.get("x-request-start", "")
            except Exception:
                pass
            else:
                track_request_queue_time(queue_time, tracked_request)

            try:
                return callback(*args, **kwargs)
            except Exception:
                tracked_request.tag("error", "true")
                raise
            finally:
                tracked_request.stop_span()

        return wrapper
