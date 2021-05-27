# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

import django
from django.conf import settings

from scout_apm.compat import string_types
from scout_apm.core.config import scout_config
from scout_apm.core.error import ErrorMonitor
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import (
    RequestComponents,
    create_filtered_path,
    ignore_path,
    track_amazon_request_queue_time,
    track_request_queue_time,
)

if django.VERSION >= (1, 11):
    from django.urls import get_urlconf
else:
    from django.core.urlresolvers import get_urlconf

if django.VERSION < (3, 2):
    from django.views.debug import get_safe_settings
else:
    from django.views.debug import SafeExceptionReporterFilter

    def get_safe_settings():
        return SafeExceptionReporterFilter().get_safe_settings()


def get_controller_name(request):
    view_func = request.resolver_match.func
    view_name = request.resolver_match._func_path

    django_admin_components = _get_django_admin_components(view_func)
    if django_admin_components:
        view_name = "{}.{}.{}".format(
            django_admin_components.module,
            django_admin_components.controller,
            django_admin_components.action,
        )

    django_rest_framework_components = _get_django_rest_framework_components(
        request, view_func, view_name
    )
    if django_rest_framework_components is not None:
        view_name = "{}.{}".format(
            django_rest_framework_components.controller,
            django_rest_framework_components.action,
        )

    # Seems to be a Tastypie Resource. Need to resort to some stack inspection
    # to find a better name since its decorators don't wrap very well
    if view_name == "tastypie.resources.wrapper":
        tastypie_components = _get_tastypie_components(request, view_func)
        if tastypie_components is not None:
            view_name = "{}.{}.{}".format(
                tastypie_components.module,
                tastypie_components.controller,
                tastypie_components.action,
            )

    return "Controller/{}".format(view_name)


def get_request_components(request):
    view_func = request.resolver_match.func
    view_name = request.resolver_match._func_path
    request_components = RequestComponents(
        module=view_func.__module__,
        controller=view_func.__name__,
        action=request.method,
    )

    django_admin_components = _get_django_admin_components(view_func)
    if django_admin_components:
        request_components = django_admin_components

    django_rest_framework_components = _get_django_rest_framework_components(
        request, view_func, view_name
    )
    if django_rest_framework_components is not None:
        request_components = django_rest_framework_components

    # Seems to be a Tastypie Resource. Need to resort to some stack inspection
    # to find a better name since its decorators don't wrap very well
    if view_name == "tastypie.resources.wrapper":
        tastypie_components = _get_tastypie_components(request, view_func)
        if tastypie_components is not None:
            request_components = tastypie_components
    return request_components


def _get_django_admin_components(view_func):
    if hasattr(view_func, "model_admin"):
        # Seems to comes from Django admin (attribute only set on Django 1.9+)
        admin_class = view_func.model_admin.__class__
        return RequestComponents(
            module=admin_class.__module__,
            controller=admin_class.__name__,
            action=view_func.__name__,
        )
    return None


def _get_django_rest_framework_components(request, view_func, view_name):
    try:
        from rest_framework.viewsets import ViewSetMixin
    except ImportError:
        return None

    kls = getattr(view_func, "cls", None)
    if isinstance(kls, type) and not issubclass(kls, ViewSetMixin):
        return None

    # Get 'actions' set in ViewSetMixin.as_view
    actions = getattr(view_func, "actions", None)
    if not actions or not isinstance(actions, dict):
        return None

    method_lower = request.method.lower()
    if method_lower not in actions:
        return None

    return RequestComponents(
        module=view_func.__module__,
        controller=view_name,
        action=actions[method_lower],
    )


def _get_tastypie_components(request, view_func):
    try:
        from tastypie.resources import Resource
    except ImportError:
        return None

    if sys.version_info[0] == 2:  # pragma: no cover
        try:
            wrapper = view_func.__closure__[0].cell_contents
        except (AttributeError, IndexError):
            return None
    else:
        try:
            wrapper = view_func.__wrapped__
        except AttributeError:
            return None

    if not hasattr(wrapper, "__closure__") or len(wrapper.__closure__) != 2:
        return None

    instance = wrapper.__closure__[0].cell_contents
    if not isinstance(instance, Resource):  # pragma: no cover
        return None

    method_name = wrapper.__closure__[1].cell_contents
    if not isinstance(method_name, string_types):  # pragma: no cover
        return None

    if method_name.startswith("dispatch_"):  # pragma: no cover
        method_name = request.method.lower() + method_name.split("dispatch", 1)[1]

    return RequestComponents(
        module=instance.__module__,
        controller=instance.__class__.__name__,
        action=method_name,
    )


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

    if scout_config.value("collect_remote_ip"):
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

    # Django's request.user caches in this attribute on first access. We only
    # want to track the user if the application code has touched request.user
    # because touching it causes session access, which adds "Cookie" to the
    # "Vary" header.
    user = getattr(request, "_cached_user", None)
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
        if not scout_config.value("monitor"):
            return self.get_response(request)

        tracked_request = TrackedRequest.instance()

        queue_time = request.META.get("HTTP_X_QUEUE_START") or request.META.get(
            "HTTP_X_REQUEST_START", ""
        )
        queue_time_tracked = track_request_queue_time(queue_time, tracked_request)
        if not queue_time_tracked:
            track_amazon_request_queue_time(
                request.META.get("HTTP_X_AMZN_TRACE_ID", ""), tracked_request
            )

        with tracked_request.span(
            operation="Middleware",
            should_capture_backtrace=False,
        ):
            return self.get_response(request)

    def process_exception(self, request, exception):
        """
        Process this exception with the error monitoring solution.

        Does not modify or otherwise change the exception thrown
        """
        path = create_filtered_path(
            request.path, [(k, v) for k, vs in request.GET.lists() for v in vs]
        )
        ErrorMonitor.send(
            exception,
            path=path,
            params=request.GET.dict(),
            session=dict(request.session.items()),
            request_components=get_request_components(request),
            environment=get_safe_settings(),
        )


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
        if not scout_config.value("monitor"):
            return self.get_response(request)

        tracked_request = TrackedRequest.instance()

        # This operation name won't be recorded unless changed later in
        # process_view
        with tracked_request.span(operation="Unknown", should_capture_backtrace=False):
            response = self.get_response(request)
            track_request_view_data(request, tracked_request)
            if 500 <= response.status_code <= 599:
                tracked_request.tag("error", "true")
            return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Capture details about the view_func that is about to execute
        """
        if not scout_config.value("monitor"):
            return
        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True

        span = tracked_request.current_span()
        if span is not None:
            span.operation = get_controller_name(request)

    def process_exception(self, request, exception):
        """
        Mark this request as having errored out

        Does not modify or catch or otherwise change the exception thrown
        """
        if not scout_config.value("monitor"):
            return
        TrackedRequest.instance().tag("error", "true")


class OldStyleMiddlewareTimingMiddleware(object):
    """
    Insert as early into the Middleware stack as possible (outermost layers),
    so that other middlewares called after can be timed.
    """

    def process_request(self, request):
        if not scout_config.value("monitor"):
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

        tracked_request.start_span(
            operation="Middleware", should_capture_backtrace=False
        )

    def process_response(self, request, response):
        # Only stop span if there's a request, but presume we are balanced,
        # i.e. that custom instrumentation within the application is not
        # causing errors
        tracked_request = getattr(request, "_scout_tracked_request", None)
        if 500 <= response.status_code <= 599:
            tracked_request.tag("error", "true")
        if tracked_request is not None:
            tracked_request.stop_span()
        return response

    def process_exception(self, request, exception):
        path = create_filtered_path(
            request.path, [(k, v) for k, vs in request.GET.lists() for v in vs]
        )
        ErrorMonitor.send(
            exception,
            path=path,
            params=request.GET.dict(),
            session=dict(request.session.items()),
            request_components=get_request_components(request),
            environment=get_safe_settings(),
        )


class OldStyleViewMiddleware(object):
    def process_view(self, request, view_func, view_func_args, view_func_kwargs):
        tracked_request = getattr(request, "_scout_tracked_request", None)
        if tracked_request is None:
            # Looks like OldStyleMiddlewareTimingMiddleware didn't run, so
            # don't do anything
            return

        tracked_request.is_real_request = True

        span = tracked_request.start_span(
            operation=get_controller_name(request), should_capture_backtrace=False
        )
        # Save the span into the request, so we can check
        # if we're matched up when stopping
        request._scout_view_span = span

    def process_response(self, request, response):
        tracked_request = getattr(request, "_scout_tracked_request", None)
        if tracked_request is None:
            # Looks like OldStyleMiddlewareTimingMiddleware didn't run, so
            # don't do anything
            return response

        track_request_view_data(request, tracked_request)

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
