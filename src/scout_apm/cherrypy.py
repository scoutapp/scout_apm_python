# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import cherrypy
from cherrypy.lib.encoding import ResponseEncoder
from cherrypy.process import plugins

from scout_apm.compat import parse_qsl
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_amazon_request_queue_time,
    track_request_queue_time,
)


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

        # Determine a remote IP to associate with the request. The value is
        # spoofable by the requester so this is not suitable to use in any
        # security sensitive context.
        user_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0]
            or request.headers.get("client-ip", "").split(",")[0]
            or (request.remote.ip or None)
        )
        tracked_request.tag("user_ip", user_ip)

        queue_time = request.headers.get("x-queue-start", "") or request.headers.get(
            "x-request-start", ""
        )
        tracked_queue_time = track_request_queue_time(queue_time, tracked_request)
        if not tracked_queue_time:
            amazon_queue_time = request.headers.get("x-amzn-trace-id", "")
            track_amazon_request_queue_time(amazon_queue_time, tracked_request)

        response = cherrypy.response
        status = response.status.split(" ", 1)[0]
        try:
            status_int = int(status)
        except ValueError:
            pass
        else:
            if 500 <= status_int <= 599:
                tracked_request.tag("error", "true")

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

    # TODO: handle 404's
    # ERROR    cherrypy.error:_cplogging.py:216 [24/Dec/2019:15:45:09] ENGINE Error in 'after_request' listener <bound method ScoutPlugin.after_request of <scout_apm.cherrypy.ScoutPlugin object at 0x10a659c50>>
    # Traceback (most recent call last):
    #   File "/Users/chainz/Documents/Projects/scout_apm_python/.tox/py37-django30/lib/python3.7/site-packages/cherrypy/process/wspbus.py", line 230, in publish
    #     output.append(listener(*args, **kwargs))
    #   File "/Users/chainz/Documents/Projects/scout_apm_python/.tox/py37-django30/lib/python3.7/site-packages/scout_apm/cherrypy.py", line 41, in after_request
    #     operation_name = get_operation_name(request)
    #   File "/Users/chainz/Documents/Projects/scout_apm_python/.tox/py37-django30/lib/python3.7/site-packages/scout_apm/cherrypy.py", line 90, in get_operation_name
    #     real_handler.__func__.__module__, real_handler.__func__.__name__
    # AttributeError: 'NotFound' object has no attribute '__func__'

    real_handler_cls = real_handler.__self__.__class__
    return "Controller/{}.{}.{}".format(
        real_handler_cls.__module__, real_handler_cls.__name__, real_handler.__name__,
    )
