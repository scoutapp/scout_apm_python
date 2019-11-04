# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import wrapt
from flask import current_app
from flask.globals import _request_ctx_stack

import scout_apm.core
from scout_apm.core.config import scout_config
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import werkzeug_track_request_data


class ScoutApm(object):
    def __init__(self, app):
        self.app = app
        app.before_first_request(self.before_first_request)
        app.dispatch_request = self.wrapped_dispatch_request(app.dispatch_request)

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
        scout_config.set(**configs)

    ############################
    #  Request Lifecycle hook  #
    ############################

    @wrapt.decorator
    def wrapped_dispatch_request(self, wrapped, instance, args, kwargs):
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
        tracked_request.is_real_request = True
        span = tracked_request.start_span(
            operation=operation, should_capture_backtrace=False
        )
        span.tag("name", name)

        werkzeug_track_request_data(request, tracked_request)

        try:
            return wrapped(*args, **kwargs)
        except Exception as exc:
            tracked_request.tag("error", "true")
            raise exc
        finally:
            tracked_request.stop_span()
