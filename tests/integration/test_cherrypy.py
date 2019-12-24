# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
from contextlib import contextmanager

import cherrypy
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.cherrypy import ScoutPlugin
from scout_apm.compat import datetime_to_timestamp
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)


@contextmanager
def app_with_scout(scout_config=None):
    """
    Context manager that configures and installs the Scout plugin for CherryPy.
    """
    if scout_config is None:
        scout_config = {}

    scout_config["core_agent_launch"] = False
    scout_config.setdefault("monitor", True)
    Config.set(**scout_config)

    class Views(object):
        @cherrypy.expose
        def index(self, **params):  # Take all params so CherryPy doesn't 404
            return "Welcome home."

        @cherrypy.expose
        def hello(self):
            return "Hello World!"

        @cherrypy.expose
        def crash(self):
            raise ValueError("BØØM!")  # non-ASCII

        @cherrypy.expose
        def return_error(self):
            cherrypy.response.status = 503
            return "Something went wrong"

    app = cherrypy.Application(Views(), "/", config=None)

    # Setup according to https://docs.scoutapm.com/#cherrypy
    plugin = ScoutPlugin(cherrypy.engine)
    plugin.subscribe()

    try:
        yield app
    finally:
        plugin.unsubscribe()
        Config.reset_all()


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
    assert span.operation == "Controller/tests.integration.test_cherrypy.Views.index"


def test_home_ignored(tracked_requests):
    with app_with_scout(scout_config={"ignore": "/"}) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert tracked_requests == []


@parametrize_filtered_params
def test_filtered_params(params, expected_path, tracked_requests):
    with app_with_scout() as app:
        TestApp(app).get("/", params=params)

    assert tracked_requests[0].tags["path"] == expected_path


@parametrize_user_ip_headers
def test_user_ip(headers, client_address, expected, tracked_requests):
    with app_with_scout() as app:
        TestApp(app).get(
            "/",
            headers=headers,
            extra_environ=(
                {str("REMOTE_ADDR"): client_address}
                if client_address is not None
                else {}
            ),
        )

    tracked_request = tracked_requests[0]
    assert tracked_request.tags["user_ip"] == expected


@parametrize_queue_time_header_name
def test_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    with app_with_scout() as app:
        response = TestApp(app).get(
            "/", headers={header_name: str("t=") + str(queue_start)}
        )

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


def test_amazon_queue_time(tracked_requests):
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    with app_with_scout() as app:
        response = TestApp(app).get(
            "/",
            headers={
                "X-Amzn-Trace-Id": str(
                    "Self=1-{}-12456789abcdef012345678".format(queue_start)
                )
            },
        )

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


def test_hello(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert response.text == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/hello/"
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/tests.integration.test_cherrypy.Views.hello"


def test_server_error(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/crash/", expect_errors=True)

    assert response.status_int == 500
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/crash/"
    assert tracked_request.tags["error"] == "true"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/tests.integration.test_cherrypy.Views.crash"


def test_return_error(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/return-error/", expect_errors=True)

    assert response.status_int == 503
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/return-error/"
    assert tracked_request.tags["error"] == "true"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert (
        span.operation
        == "Controller/tests.integration.test_cherrypy.Views.return_error"
    )


def test_no_monitor(tracked_requests):
    with app_with_scout(scout_config={"monitor": False}) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert tracked_requests == []
