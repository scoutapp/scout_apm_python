from flask import current_app, request, g, send_from_directory
from flask.globals import _request_ctx_stack

from datetime import datetime


class ScoutApm(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.before_request(self.process_request)
        app.after_request(self.process_response)
        app.teardown_request(self.teardown_request)

        # Monkey-patch the Flask.dispatch_request method
        app.dispatch_request = self.dispatch_request

    def dispatch_request(self):
        """Modified version of Flask.dispatch_request to call process_view."""

        print("Dispatch Request")
        req = _request_ctx_stack.top.request
        app = current_app

        if req.routing_exception is not None:
            app.raise_routing_exception(req)

        rule = req.url_rule

        # if we provide automatic options for this URL and the
        # request came with the OPTIONS method, reply automatically
        if getattr(rule, 'provide_automatic_options', False) \
           and req.method == 'OPTIONS':
            return app.make_default_options_response()

        # otherwise dispatch to the handler for that endpoint
        view_func = app.view_functions[rule.endpoint]
        view_func = self.process_view(app, view_func, req.view_args)

        return view_func(**req.view_args)

    def process_request(self):
        print("Process Request")

    def process_view(self, app, view_func, view_kwargs):
        """ This method is called just before the flask view is called.
        This is done by the dispatch_request method.
        """
        print("Process View:", view_func.__module__, view_func.__name__)
        #  __import__('pdb').set_trace()
        return view_func

    def process_response(self, response):
        print("Process Response")
        return response

    def teardown_request(self, exc):
        print("Teardown Request")


