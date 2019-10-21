# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from flask import current_app
from flask.globals import _request_ctx_stack

import scout_apm.core
from scout_apm.core.config import ScoutConfig
from scout_apm.core.monkey import CallableProxy
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_amazon_request_queue_time,
    track_request_queue_time,
)


class ScoutApm(object):
    def __init__(self, app):
        self.app = app
        app.before_first_request(self.before_first_request)
        # Wrap the Flask.dispatch_request method
        app.dispatch_request = CallableProxy(
            app.dispatch_request, self.wrapped_dispatch_request
        )

    #############
    #  Startup  #
    #############

    def before_first_request(self):
        self.extract_flask_settings()
        installed = scout_apm.core.install()
        self._do_nothing = not installed

    def extract_flask_settings(self):
        """
        Copies SCOUT_* settings in the app into Scout's config lookup
        """
        configs = {}
        configs["application_root"] = self.app.instance_path
        for name in current_app.config:
            if name.startswith("SCOUT_"):
                value = current_app.config[name]
                clean_name = name.replace("SCOUT_", "").lower()
                configs[clean_name] = value
        ScoutConfig.set(**configs)

    ############################
    #  Request Lifecycle hook  #
    ############################

    def wrapped_dispatch_request(self, wrapped, *args, **kwargs):
        if self._do_nothing:
            return wrapped(*args, **kwargs)

        request = _request_ctx_stack.top.request

        # Copied logic from Flask
        if request.routing_exception is not None:
            return wrapped(*args, **kwargs)

        rule = request.url_rule
        view_func = self.app.view_functions[rule.endpoint]

        name = view_func.__module__ + "." + view_func.__name__
        operation = "Controller/" + name

        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()
        span = tracked_request.start_span(operation=operation)
        span.tag("name", name)

        path = request.path
        tracked_request.tag(
            "path", create_filtered_path(path, request.args.items(multi=True))
        )
        if ignore_path(path):
            tracked_request.tag("ignore_transaction", True)

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
        tracked = track_request_queue_time(queue_time, tracked_request)
        if not tracked:
            amazon_queue_time = request.headers.get("x-amzn-trace-id", default="")
            track_amazon_request_queue_time(amazon_queue_time, tracked_request)

        try:
            return wrapped(*args, **kwargs)
        except Exception as exc:
            tracked_request.tag("error", "true")
            raise exc
        finally:
            tracked_request.stop_span()
