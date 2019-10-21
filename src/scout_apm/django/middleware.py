# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import django
from django.conf import settings

from scout_apm.core.config import ScoutConfig
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    create_filtered_path,
    ignore_path,
    track_amazon_request_queue_time,
    track_request_queue_time,
)

if django.VERSION >= (2, 0):
    from django.urls import get_urlconf
else:
    from django.core.urlresolvers import get_urlconf


def get_operation_name(request):
    view_func = request.resolver_match.func
    view_name = request.resolver_match._func_path

    if hasattr(view_func, "model_admin"):
        # Seems to comes from Django admin (attribute only set on Django 1.9+)
        admin_class = view_func.model_admin.__class__
        view_name = (
            admin_class.__module__
            + "."
            + admin_class.__name__
            + "."
            + view_func.__name__
        )

    return "Controller/" + view_name


def track_request_view_data(request, tracked_request):
    path = request.path
    tracked_request.tag(
        "path",
        create_filtered_path(
            path, [(k, v) for k, vs in request.GET.lists() for v in vs]
        ),
    )
    if ignore_path(path):
        tracked_request.tag("ignore_transaction", True)

    try:
        # Determine a remote IP to associate with the request. The value is
        # spoofable by the requester so this is not suitable to use in any
        # security sensitive context.
        user_ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0]
            or request.META.get("HTTP_CLIENT_IP", "").split(",")[0]
            or request.META.get("REMOTE_ADDR", None)
        )
        tracked_request.tag("user_ip", user_ip)
    except Exception:
        pass

    user = getattr(request, "user", None)
    if user is not None:
        try:
            tracked_request.tag("username", user.get_username())
        except Exception:
            pass

    tracked_request.tag("urlconf", get_urlconf(settings.ROOT_URLCONF))


class MiddlewareTimingMiddleware(object):
    """
    Insert as early into the Middleware stack as possible (outermost layers),
    so that other middlewares called after can be timed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not ScoutConfig().value("monitor"):
            return self.get_response(request)

        tracked_request = TrackedRequest.instance()

        tracked_request.start_span(operation="Middleware")
        queue_time = request.META.get("HTTP_X_QUEUE_START") or request.META.get(
            "HTTP_X_REQUEST_START", ""
        )
        queue_time_tracked = track_request_queue_time(queue_time, tracked_request)
        if not queue_time_tracked:
            track_amazon_request_queue_time(
                request.META.get("HTTP_X_AMZN_TRACE_ID", ""), tracked_request
            )

        try:
            return self.get_response(request)
        finally:
            tracked_request.stop_span()


class ViewTimingMiddleware(object):
    """
    Insert as deep into the middleware stack as possible, ideally wrapping no
    other middleware. Designed to time the View itself
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Wrap a single incoming request with start and stop calls.
        This will start timing, but relies on the process_view callback to
        capture more details about what view was really called, and other
        similar info.

        If process_view isn't called, then the request will not
        be recorded.  This can happen if a middleware further along the stack
        doesn't call onward, and instead returns a response directly.
        """
        if not ScoutConfig().value("monitor"):
            return self.get_response(request)

        tracked_request = TrackedRequest.instance()

        # This operation name won't be recorded unless changed later in
        # process_view
        tracked_request.start_span(operation="Unknown")
        try:
            return self.get_response(request)
        finally:
            tracked_request.stop_span()

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Capture details about the view_func that is about to execute
        """
        if not ScoutConfig().value("monitor"):
            return
        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()

        track_request_view_data(request, tracked_request)

        span = tracked_request.current_span()
        if span is not None:
            span.operation = get_operation_name(request)

    def process_exception(self, request, exception):
        """
        Mark this request as having errored out

        Does not modify or catch or otherwise change the exception thrown
        """
        if not ScoutConfig().value("monitor"):
            return
        TrackedRequest.instance().tag("error", "true")


class OldStyleMiddlewareTimingMiddleware(object):
    """
    Insert as early into the Middleware stack as possible (outermost layers),
    so that other middlewares called after can be timed.
    """

    def process_request(self, request):
        if not ScoutConfig().value("monitor"):
            return
        tracked_request = TrackedRequest.instance()
        request._scout_tracked_request = tracked_request

        queue_time = request.META.get("HTTP_X_QUEUE_START") or request.META.get(
            "HTTP_X_REQUEST_START", ""
        )
        queue_time_tracked = track_request_queue_time(queue_time, tracked_request)
        if not queue_time_tracked:
            track_amazon_request_queue_time(
                request.META.get("HTTP_X_AMZN_TRACE_ID", ""), tracked_request
            )

        tracked_request.start_span(operation="Middleware")

    def process_response(self, request, response):
        # Only stop span if there's a request, but presume we are balanced,
        # i.e. that custom instrumentation within the application is not
        # causing errors
        tracked_request = getattr(request, "_scout_tracked_request", None)
        if tracked_request is not None:
            tracked_request.stop_span()
        return response


class OldStyleViewMiddleware(object):
    def process_view(self, request, view_func, view_func_args, view_func_kwargs):
        tracked_request = getattr(request, "_scout_tracked_request", None)
        if tracked_request is None:
            # Looks like OldStyleMiddlewareTimingMiddleware didn't run, so
            # don't do anything
            return

        tracked_request.mark_real_request()

        track_request_view_data(request, tracked_request)

        span = tracked_request.start_span(operation=get_operation_name(request))
        # Save the span into the request, so we can check
        # if we're matched up when stopping
        request._scout_view_span = span

    def process_response(self, request, response):
        tracked_request = getattr(request, "_scout_tracked_request", None)
        if tracked_request is None:
            # Looks like OldStyleMiddlewareTimingMiddleware didn't run, so
            # don't do anything
            return response

        # Only stop span if we started, but presume we are balanced, i.e. that
        # custom instrumentation within the application is not causing errors
        span = getattr(request, "_scout_view_span", None)
        if span is not None:
            tracked_request.stop_span()
        return response

    def process_exception(self, request, exception):
        tracked_request = getattr(request, "_scout_tracked_request", None)
        if tracked_request is None:
            # Looks like OldStyleMiddlewareTimingMiddleware didn't run, so
            # don't do anything
            return

        tracked_request.tag("error", "true")
