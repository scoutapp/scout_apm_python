# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import cherrypy
from cherrypy.lib.encoding import ResponseEncoder
from cherrypy.process import plugins

import scout_apm.core
from scout_apm.compat import parse_qsl
from scout_apm.core.config import scout_config
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_request_queue_time,
)


class ScoutPlugin(plugins.SimplePlugin):
    def __init__(self, bus):
        super(ScoutPlugin, self).__init__(bus)
        installed = scout_apm.core.install()
        self._do_nothing = not installed

    def before_request(self):
        if self._do_nothing:
            return
        request = cherrypy.request
        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True
        request._scout_tracked_request = tracked_request

        # Can't name operation until after request, when routing has been done
        request._scout_controller_span = tracked_request.start_span(
            "Controller/Unknown"
        )

    def after_request(self):
        if self._do_nothing:
            return
        request = cherrypy.request
        tracked_request = getattr(request, "_scout_tracked_request", None)
        if tracked_request is None:
            return

        # Rename controller span now routing has been done
        operation_name = get_operation_name(request)
        if operation_name is not None:
            request._scout_controller_span.operation = operation_name

        # Grab general request data now it has been parsed
        path = request.path_info
        # Parse params ourselves because we want only GET params but CherryPy
        # parses POST params (nearly always sensitive) into the same dict.
        params = parse_qsl(request.query_string)
        tracked_request.tag("path", create_filtered_path(path, params))
        if ignore_path(path):
            tracked_request.tag("ignore_transaction", True)

        if scout_config.value("collect_remote_ip"):
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
        track_request_queue_time(queue_time, tracked_request)

        response = cherrypy.response
        status = response.status
        if isinstance(status, int):
            status_int = status
        else:
            status_first = status.split(" ", 1)[0]
            try:
                status_int = int(status_first)
            except ValueError:
                # Assume OK
                status_int = 200
        if 500 <= status_int <= 599:
            tracked_request.tag("error", "true")
        elif status_int == 404:
            tracked_request.is_real_request = False

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

    # Looks like it's from HandlerTool
    if getattr(real_handler, "__name__", "") == "handle_func":
        try:
            wrapped_tool = real_handler.__closure__[2].cell_contents.callable
        except (AttributeError, IndexError):
            pass
        else:
            try:
                return "Controller/{}".format(wrapped_tool.__name__)
            except AttributeError:
                pass

    # Not a method? Not from an exposed view then
    if not hasattr(real_handler, "__self__"):
        return None

    real_handler_cls = real_handler.__self__.__class__
    return "Controller/{}.{}.{}".format(
        real_handler_cls.__module__,
        real_handler_cls.__name__,
        real_handler.__name__,
    )
