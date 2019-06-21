# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import inspect

from scout_apm.api import install
from scout_apm.core.ignore import ignore_path
from scout_apm.core.tracked_request import TrackedRequest

# Falcon Middleware docs:
# https://falcon.readthedocs.io/en/stable/api/middleware.html


class ScoutMiddleware(object):
    """
    Falcon Middleware for integration with Scout APMi.
    """

    def __init__(self, config):
        install(config=config)

    def process_request(self, req, resp):
        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()
        req.context.scout_tracked_request = tracked_request

        tracked_request.tag("path", req.path)

        if ignore_path(req.path):
            tracked_request.tag("ignore_transaction", True)

    def process_resource(self, req, resp, resource, params):
        tracked_request = getattr(req.context, "scout_tracked_request", None)
        if tracked_request is None:
            # Somehow we didn't start a request - this might occur in
            # combination with a pretty adversarial application, so guard
            # against it, although if a request was started and the context was
            # lost, other problems might occur.
            return  # pragma: no cover

        # Find the current responder's name. Falcon passes middleware the
        # current resource but unfortunately not the method being called. Also
        # middleware doesn't have a reference to the current API object so we
        # can't check the router there. Use some hopefully pretty harmless
        # stack inspection to look up the current responder method.
        responder_name = None
        current_frame = inspect.currentframe()
        # current_frame can return None if stack inspection is not available
        if current_frame is not None:
            try:
                if current_frame.f_back is not None:
                    responder = current_frame.f_back.f_locals.get("responder", None)
                    if responder is not None:
                        responder_name = getattr(responder, "__name__", None)
            finally:
                # As per inspect docs, one should always be careful to release
                # references to frames
                del current_frame

        if responder_name is not None:
            operation = "Controller/{}.{}.{}".format(
                resource.__module__, resource.__class__.__name__, responder_name
            )
        else:
            # Since we couldn't find the current responder method, instead use
            # a slash and the HTTP method name
            operation = "Controller/{}.{}/{}".format(
                resource.__module__, resource.__class__.__name__, req.method
            )

        span = tracked_request.start_span(operation=operation)
        req.context.scout_resource_span = span

    def process_response(self, req, resp, resource, req_succeeded):
        tracked_request = getattr(req.context, "scout_tracked_request", None)
        if tracked_request is None:
            # Somehow we didn't start a request
            return

        if not req_succeeded:
            tracked_request.tag("error", "true")

        span = getattr(req.context, "scout_resource_span", None)
        if span is not None:
            tracked_request.stop_span()
        else:
            tracked_request.finish()
