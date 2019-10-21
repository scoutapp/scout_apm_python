# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import sys
from contextlib import contextmanager

from bottle import Bottle, WSGIHeaderDict
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.bottle import ScoutPlugin
from scout_apm.compat import datetime_to_timestamp
from tests.compat import mock
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)


@contextmanager
def app_with_scout(config=None, catchall=False):
    """
    Context manager that configures and installs the Scout plugin for Bottle.
    """
    if config is None:
        config = {}

    # Enable Scout by default in tests.
    config.setdefault("scout.monitor", True)

    # Disable running the agent.
    config["scout.core_agent_launch"] = False

    app = Bottle(catchall=catchall)

    @app.route("/")
    def home():
        return "Welcome home."

    @app.route("/hello/")
    def hello():
        return "Hello World!"

    @app.route("/crash/")
    def crash():
        raise ValueError("BØØM!")  # non-ASCII

    @app.route("/named/", name="named_route")
    def named():
        return "Response from a named route."

    # Setup according to https://docs.scoutapm.com/#bottle
    app.config.update(config)
    scout = ScoutPlugin()
    app.install(scout)

    try:
        yield app
    finally:
        # Reset Scout configuration.
        Config.reset_all()


def test_home(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.tags["user_ip"] is None
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/home"


@parametrize_filtered_params
def test_filtered_params(params, expected_path, tracked_requests):
    with app_with_scout() as app:
        TestApp(app).get("/", params=params)

    assert tracked_requests[0].tags["path"] == expected_path


@parametrize_user_ip_headers
def test_user_ip(headers, extra_environ, expected, tracked_requests):
    if sys.version_info[0] == 2:
        # Required for WebTest lint
        headers = {str(k): str(v) for k, v in headers.items()}
        extra_environ = {str(k): str(v) for k, v in extra_environ.items()}

    with app_with_scout() as app:
        TestApp(app).get("/", headers=headers, extra_environ=extra_environ)

    tracked_request = tracked_requests[0]
    assert tracked_request.tags["user_ip"] == expected


def test_user_ip_error(tracked_requests):
    orig_headers_get = WSGIHeaderDict.get

    def crashy_get(self, key, *args, **kwargs):
        if key == "x-forwarded-for":
            raise ValueError("Don't try get *that* header!")
        return orig_headers_get(key, *args, **kwargs)

    with mock.patch.object(
        WSGIHeaderDict, "get", new=crashy_get
    ), app_with_scout() as app:
        TestApp(app).get("/")

    tracked_request = tracked_requests[0]
    assert "user_ip" not in tracked_request.tags


@parametrize_queue_time_header_name
def test_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow()) - 2)
    with app_with_scout() as app:
        response = TestApp(app).get(
            "/", headers={header_name: str("t=") + str(queue_start)}
        )

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


def test_queue_time_error(tracked_requests):
    """
    Scout doesn't crash if bottle's Request.headers.get raises an exception.

    This cannot be tested without mocking because it should never happen.
    """
    orig_headers_get = WSGIHeaderDict.get

    def crashy_get(self, key, *args, **kwargs):
        if key == "x-queue-start":
            raise ValueError("Don't try get *that* header!")
        return orig_headers_get(key, *args, **kwargs)

    with mock.patch.object(
        WSGIHeaderDict, "get", new=crashy_get
    ), app_with_scout() as app:
        TestApp(app).get("/")

    tracked_request = tracked_requests[0]
    assert "scout.queue_time_ns" not in tracked_request.tags


def test_amazon_queue_time(tracked_requests):
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow()) - 2)
    with app_with_scout() as app:
        response = TestApp(app).get(
            "/",
            headers={
                "X-Amzn-Trace-Id": str("Self=1-{}-12456789abcdef012345678".format(
                    queue_start
                ))
            },
        )

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


def test_home_ignored(tracked_requests):
    with app_with_scout({"scout.ignore": ["/"]}) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert tracked_requests == []


def test_hello(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert response.text == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/hello/"
    assert tracked_request.tags["user_ip"] is None
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/hello/"


def test_not_found(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/not-found/", expect_errors=True)

    assert response.status_int == 404
    assert tracked_requests == []


def test_server_error(tracked_requests):
    with app_with_scout(catchall=True) as app:
        response = TestApp(app).get("/crash/", expect_errors=True)

    assert response.status_int == 500
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["error"] == "true"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_requests[0].complete_spans[0]
    assert span.operation == "Controller/crash/"


def test_named(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/named/")

    assert response.status_int == 200
    assert response.text == "Response from a named route."
    assert len(tracked_requests) == 1
    assert len(tracked_requests[0].complete_spans) == 1
    span = tracked_requests[0].complete_spans[0]
    assert span.operation == "Controller/named_route"


def test_no_monitor(tracked_requests):
    with app_with_scout({"scout.monitor": False}) as app:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert response.text == "Hello World!"
    assert tracked_requests == []
