# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
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
        self.api = None
        self._attempted_to_discover_api = False
        installed = install(config=config)
        self._do_nothing = not installed

    def set_api(self, api):
        if not isinstance(api, falcon.API):
            raise ValueError("api should be an instance of falcon.API")
        self.api = api

    def _discover_api(self):
        """
        Discover the Falcon API this middleware is attached to via stack
        inspection. If it fails, record the fact, so we don't attempt it again.
        """
        if self._attempted_to_discover_api:
            return
        self._attempted_to_discover_api = True
        try:
            frame = inspect.currentframe()
            process_request_frame = frame.f_back
            API_call_frame = process_request_frame.f_back
            self.api = API_call_frame.f_locals["self"]
        except Exception:  # pragma: no cover
            pass

    def process_request(self, req, resp):
        if self._do_nothing:
            return
        if self.api is None:
            self._discover_api()
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
        if self._do_nothing:
            return

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
                    "Automatic API object discovery failed. Call {}.set_api()"
                    " before requests begin to enable more detail to be"
                    " captured."
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
            try:
                last_part = responder.__name__
            except AttributeError:
                last_part = req.method
            operation = "Controller/{}.{}.{}".format(
                resource.__module__, resource.__class__.__name__, last_part
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

        # Falcon only stores the response status line, we have to parse it
        try:
            status_code = int(resp.status.split(" ")[0])
        except ValueError:
            # Bad status line - force it to be tagged as an error because
            # client will experience it as one
            status_code = 500

        if not req_succeeded or 500 <= status_code <= 599:
            tracked_request.tag("error", "true")

        span = getattr(req.context, "scout_resource_span", None)
        if span is not None:
            tracked_request.stop_span()
        else:
            tracked_request.finish()
