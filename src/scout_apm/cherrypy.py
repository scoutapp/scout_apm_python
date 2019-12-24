# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import cherrypy
from cherrypy.lib.encoding import ResponseEncoder
from cherrypy.process import plugins

from scout_apm.compat import parse_qsl
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import create_filtered_path, ignore_path


class ScoutPlugin(plugins.SimplePlugin):
    def __init__(self, bus):
        super(ScoutPlugin, self).__init__(bus)

    def before_request(self):
        request = cherrypy.request
        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True
        request._scout_tracked_request = tracked_request

        # Can't name operation until after request, when routing has been done
        request._scout_controller_span = tracked_request.start_span(
            "Controller/Unknown"
        )

    def after_request(self):
        tracked_request = getattr(cherrypy.request, "_scout_tracked_request", None)
        if tracked_request is None:
            return

        request = cherrypy.request

        # Rename controller span now routing has been done
        operation_name = get_operation_name(request)
        if operation_name is not None:
            request._scout_controller_span.operation = operation_name

        # Grab general request data now it has been parsed
        path = request.path_info
        # Parse params because we want only GET params but CherryPy parses
        # POST params into the same dict.
        params = parse_qsl(request.query_string)
        tracked_request.tag("path", create_filtered_path(path, params))
        if ignore_path(path):
            tracked_request.tag("ignore_transaction", True)

        tracked_request.stop_span()


def get_operation_name(request):
    handler = request.handler
    if handler is None:
        return None

    if isinstance(handler, ResponseEncoder):
        real_handler = handler.oldhandler
    else:
        real_handler = handler

    # Unwrap HandlerWrapperTool classes
    while hasattr(real_handler, "callable"):
        real_handler = real_handler.callable

    return "Controller/{}.{}".format(
        real_handler.__func__.__module__, real_handler.__func__.__name__
    )
