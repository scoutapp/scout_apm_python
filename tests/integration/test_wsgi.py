# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from contextlib import contextmanager
from io import BytesIO

import pytest
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.wsgi import wrap_wsgi_application
from tests.tools import pretend_package_unavailable


@contextmanager
def app_with_scout(scout_config=None):
    """
    Context manager that configures and installs the Scout plugin for Bottle.

    """
    if scout_config is None:
        scout_config = {}
    scout_config["core_agent_launch"] = False
    scout_config.setdefault("monitor", True)
    Config.set(**scout_config)

    def app(environ, start_response):
        path = environ["PATH_INFO"]
        method = environ["REQUEST_METHOD"].lower()

        status = "200 OK"
        exc_info = None

        if path == "/":
            response = b"Welcome home."
        elif path == "/hello/":
            if method == "options":
                response = b"Hello Options!"
            elif method == "get":
                response = b"Hello World!"
            else:
                status = "405 Method Not Allowed"
                response = b"Method " + method.encode("utf-8") + " not allowed"
        elif path == "/crash/":
            raise ValueError("BØØM!")  # non-ASCII
        elif path == "/error/":
            try:
                raise ValueError("Caught error")
            except ValueError:
                exc_info = sys.exc_info()
        else:
            status = "404 Not Found"
            response = b"Resource not found"

        start_response(status, [("Content-Type", "text/plain")], exc_info)
        return BytesIO(response)

    try:
        yield wrap_wsgi_application(app)
    finally:
        Config.reset_all()


def test_werkzeug_required():
    with pretend_package_unavailable("werkzeug"):
        with pytest.raises(ImportError) as excinfo:
            wrap_wsgi_application(None)

    assert excinfo.value.args == ("No module named 'werkzeug'",)


def test_home(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/"
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/tests.integration.test_flask.home"
