from __future__ import absolute_import, division, print_function, unicode_literals

from flask import current_app
from flask.globals import _request_ctx_stack

import scout_apm.core
from scout_apm.core.config import ScoutConfig
from scout_apm.core.ignore import ignore_path
from scout_apm.core.monkey import CallableProxy
from scout_apm.core.tracked_request import TrackedRequest


class ScoutApm(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

        app.before_first_request(self.before_first_request)
        app.before_request(self.process_request)
        app.after_request(self.process_response)

        # Monkey-patch the Flask.dispatch_request method
        app.dispatch_request = self.dispatch_request

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

    #############################
    #  Request Lifecycle hooks  #
    #############################

    def dispatch_request(self):
        """Modified version of Flask.dispatch_request to call process_view."""

        req = _request_ctx_stack.top.request
        app = current_app

        # Return flask's default options response. See issue #40
        if req.method == "OPTIONS":
            return app.make_default_options_response()

        if req.routing_exception is not None:
            app.raise_routing_exception(req)

        # The routing rule has some handy attributes to extract how Flask found
        # this endpoint
        rule = req.url_rule

        # Wrap the real view_func
        view_func = self.wrap_view_func(
            app, rule, req, app.view_functions[rule.endpoint], req.view_args
        )

        return view_func(**req.view_args)

    def process_request(self):
        pass

    def wrap_view_func(self, app, rule, req, view_func, view_kwargs):
        """ This method is called just before the flask view is called.
        This is done by the dispatch_request method.
        """
        operation = view_func.__module__ + "." + view_func.__name__
        return self.trace_view_function(
            view_func, ("Controller", {"path": req.path, "name": operation})
        )

    def trace_view_function(self, func, info):
        try:

            def tracing_function(original, *args, **kwargs):
                entry_type, detail = info

                operation = entry_type
                if detail["name"] is not None:
                    operation = operation + "/" + detail["name"]

                tr = TrackedRequest.instance()
                tr.mark_real_request()
                span = tr.start_span(operation=operation)

                for key in detail:
                    span.tag(key, detail[key])

                if ignore_path(detail.get("path", "")):
                    tr.tag("ignore_transaction", True)

                # And the custom View stuff
                #  request = args[0]

                # Extract headers
                #  regex = re.compile('^HTTP_')
                #  headers = dict((regex.sub('', header), value) for (header, value)
                #  in request.META.items() if header.startswith('HTTP_'))

                #  span.tag('remote_addr', request.META['REMOTE_ADDR'])

                try:
                    return original(*args, **kwargs)
                except Exception as e:
                    TrackedRequest.instance().tag("error", "true")
                    raise e
                finally:
                    TrackedRequest.instance().stop_span()

            return CallableProxy(func, tracing_function)
        except Exception:
            # If we can't wrap for any reason, just return the original
            return func

    def process_response(self, response):
        return response
