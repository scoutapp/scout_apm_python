# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from flask import current_app
from flask.globals import _request_ctx_stack

import scout_apm.core
from scout_apm.core.config import ScoutConfig
from scout_apm.core.ignore import ignore_path
from scout_apm.core.monkey import CallableProxy
from scout_apm.core.tracked_request import TrackedRequest


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
        scout_apm.core.install()

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

    def wrapped_dispatch_request(self, original, *args, **kwargs):
        request = _request_ctx_stack.top.request

        # Copied logic from Flask
        if request.routing_exception is not None:
            return original(*args, **kwargs)

        rule = request.url_rule
        view_func = self.app.view_functions[rule.endpoint]

        path = request.path
        name = view_func.__module__ + "." + view_func.__name__
        operation = "Controller/" + name

        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()
        span = tracked_request.start_span(operation=operation)
        span.tag("path", path)
        span.tag("name", name)

        if ignore_path(path):
            tracked_request.tag("ignore_transaction", True)

        # Extract headers
        #  regex = re.compile('^HTTP_')
        #  headers = dict((regex.sub('', header), value) for (header, value)
        #  in request.META.items() if header.startswith('HTTP_'))

        #  span.tag('remote_addr', request.META['REMOTE_ADDR'])

        try:
            return original(*args, **kwargs)
        except Exception as exc:
            tracked_request.tag("error", "true")
            raise exc
        finally:
            tracked_request.stop_span()
