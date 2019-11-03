# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import falcon

from scout_apm.api import install
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_amazon_request_queue_time,
    track_request_queue_time,
)

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
        tracked_request.is_real_request = True
        req.context.scout_tracked_request = tracked_request

        path = req.path
        # Falcon URL parameter values are *either* single items or lists
        url_params = [
            (k, v)
            for k, vs in req.params.items()
            for v in (vs if isinstance(vs, list) else [vs])
        ]
        tracked_request.tag("path", create_filtered_path(path, url_params))
        if ignore_path(path):
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
        tracked_queue_time = track_request_queue_time(queue_time, tracked_request)
        if not tracked_queue_time:
            amazon_queue_time = req.get_header("x-amzn-trace-id", default="")
            track_amazon_request_queue_time(amazon_queue_time, tracked_request)

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

        span = tracked_request.start_span(
            operation=operation, should_capture_backtrace=False
        )
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
