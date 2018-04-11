import logging
from scout_apm.core.tracked_request import TrackedRequest

# Logging
logger = logging.getLogger(__name__)


class MiddlewareTimingMiddleware:
    """
    Insert as early into the Middleware stack as possible (outermost layers),
    so that other middlewares called after can be timed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        operation = 'Middleware'

        TrackedRequest.instance().start_span(operation=operation)
        response = self.get_response(request)
        TrackedRequest.instance().stop_span()
        return response

class ViewTimingMiddleware:
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

        # This operation name won't be recorded unless changed later in
        # process_view
        operation = 'Unknown'

        TrackedRequest.instance().start_span(operation=operation)
        response = self.get_response(request)
        TrackedRequest.instance().stop_span()
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Capture details about the view_func that is about to execute
        """

        view_name = request.resolver_match._func_path
        span = TrackedRequest.instance().current_span()
        if span is not None:
            span.operation = 'Controller/' + view_name
            span.tag('path', request.path)
            span.tag('remote_addr', request.META['REMOTE_ADDR'])

    def process_exception(self, request, exception):
        """
        Mark this request as having errored out

        Does not modify or catch or otherwise change the exception thrown
        """
        TrackedRequest.instance().tag('error', 'true')

    def process_template_response(self, request, response):
        """
        """
        pass
