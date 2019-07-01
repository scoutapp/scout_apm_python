# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import falcon

from scout_apm.api import install
from scout_apm.core.ignore import ignore_path
from scout_apm.core.queue_time import track_request_queue_time
from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)

# Falcon Middleware docs:
# https://falcon.readthedocs.io/en/stable/api/middleware.html


class ScoutMiddleware(object):
    """
    Falcon Middleware for integration with Scout APM.
    """

    def __init__(self, config):
        install(config=config)
        self.api = None

    def set_api(self, api):
        if not isinstance(api, falcon.API):
            raise ValueError("api should be an instance of falcon.API")
        self.api = api

    def process_request(self, req, resp):
        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()
        req.context.scout_tracked_request = tracked_request

        tracked_request.tag("path", req.path)
        if ignore_path(req.path):
            tracked_request.tag("ignore_transaction", True)

        # Determine a remote IP to associate with the request. The value is
        # spoofable by the requester so this is not suitable to use in any
        # security sensitive context.
        user_ip = (
            req.get_header("x-forwarded-for", default="").split(",")[0]
            or req.get_header("client-ip", default="").split(",")[0]
            or req.remote_addr
        )
        tracked_request.tag("user_ip", user_ip)

        queue_time = req.get_header("x-queue-start", default="") or req.get_header(
            "x-request-start", default=""
        )
        track_request_queue_time(queue_time, tracked_request)

    def process_resource(self, req, resp, resource, params):
        tracked_request = getattr(req.context, "scout_tracked_request", None)
        if tracked_request is None:
            # Somehow we didn't start a request - this might occur in
            # combination with a pretty adversarial application, so guard
            # against it, although if a request was started and the context was
            # lost, other problems might occur.
            return

        if self.api is None:
            logger.warning(
                (
                    "{}.set_api() should be called before requests begin for "
                    "more detail"
                ).format(self.__class__.__name__)
            )
            operation = "Controller/{}.{}.{}".format(
                resource.__module__, resource.__class__.__name__, req.method
            )
        else:
            # Find the current responder's name. Falcon passes middleware the
            # current resource but unfortunately not the method being called, hence
            # we have to go through routing again.
            responder, _params, _resource, _uri_template = self.api._get_responder(req)
            operation = "Controller/{}.{}.{}".format(
                resource.__module__, resource.__class__.__name__, responder.__name__
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
