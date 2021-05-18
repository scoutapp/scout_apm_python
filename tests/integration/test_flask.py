# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
from contextlib import contextmanager

import flask
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.compat import datetime_to_timestamp, kwargs_only
from scout_apm.flask import ScoutApm
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)


@contextmanager
@kwargs_only
def app_with_scout(config=None):
    """
    Context manager that configures and installs the Scout plugin for Bottle.

    """
    if config is None:
        config = {}

    config["SCOUT_CORE_AGENT_LAUNCH"] = False
    config.setdefault("SCOUT_MONITOR", True)
    # Disable Flask's error page to improve debugging
    config.setdefault("PROPAGATE_EXCEPTIONS", True)

    # Basic Flask app
    app = flask.Flask("test_app")

    @app.route("/")
    def home():
        return "Welcome home."

    @app.route("/hello/", methods=["GET", "OPTIONS"], provide_automatic_options=False)
    def hello():
        if flask.request.method == "OPTIONS":
            return "Hello Options!"
        return "Hello World!"

    @app.route("/crash/")
    def crash():
        raise ValueError("BØØM!")  # non-ASCII

    @app.route("/return-error/")
    def return_error():
        return "Something went wrong", 503

    # Setup according to https://docs.scoutapm.com/#flask
    ScoutApm(app)
    app.config.update(config)

    try:
        yield app
    finally:
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
    assert span.operation == "Controller/tests.integration.test_flask.home"


def test_home_ignored(tracked_requests):
    with app_with_scout(config={"SCOUT_MONITOR": True, "SCOUT_IGNORE": "/"}) as app:
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


def test_user_ip_collection_disabled(tracked_requests):
    with app_with_scout(config={"SCOUT_COLLECT_REMOTE_IP": False}) as app:
        TestApp(app).get(
            "/",
            extra_environ={str("REMOTE_ADDR"): str("1.1.1.1")},
        )

    tracked_request = tracked_requests[0]
    assert "user_ip" not in tracked_request.tags


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
    assert isinstance(queue_time_ns, int) and queue_time_ns > 0


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
    assert span.operation == "Controller/tests.integration.test_flask.hello"


def test_hello_options(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).options("/hello/")

    assert response.status_int == 200
    assert response.text == "Hello Options!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/hello/"
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/tests.integration.test_flask.hello"


def test_not_found(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/not-found/", expect_errors=True)

    assert response.status_int == 404
    assert tracked_requests == []


def test_server_error(tracked_requests):
    with app_with_scout(config={"PROPAGATE_EXCEPTIONS": False}) as app:
        response = TestApp(app).get("/crash/", expect_errors=True)

    assert response.status_int == 500
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/crash/"
    assert tracked_request.tags["error"] == "true"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/tests.integration.test_flask.crash"


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
    assert span.operation == "Controller/tests.integration.test_flask.return_error"


def test_automatic_options(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).options("/")

    assert response.status_int == 200
    assert response.text == ""
    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.test_flask.home"
    ]


def test_preprocessor_response(tracked_requests):
    with app_with_scout() as app:

        @app.before_request
        def teapot():
            return "I'm a teapot", 418

        response = TestApp(app).get("/", expect_errors=True)

    assert response.status_int == 418
    assert response.text == "I'm a teapot"
    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "PreprocessRequest",
        "Controller/tests.integration.test_flask.home",
    ]


def test_no_monitor(tracked_requests):
    with app_with_scout(config={"SCOUT_MONITOR": False}) as app:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert tracked_requests == []
