# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import werkzeug_track_request_data


def wrap_wsgi_application(application):
    from werkzeug.wrappers import Request

    installed = scout_apm.core.install()
    if not installed:
        return application

    def scout_wrapped_application(environ, start_response):
        request = Request(environ)
        tracked_request = TrackedRequest.instance()
        tracked_request.mark_real_request()
        operation = "Controller/{}_{}".format(request.method.lower(), request.path)
        tracked_request.start_span(operation=operation)
        werkzeug_track_request_data(request, tracked_request)

        try:
            return application(environ, start_response)
        except Exception as exc:
            tracked_request.tag("error", "true")
            raise exc
        finally:
            tracked_request.stop_span()

    return scout_wrapped_application
