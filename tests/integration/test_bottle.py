# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from bottle import Bottle
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.bottle import ScoutPlugin
from tests.compat import mock


@contextmanager
def app_with_scout(config=None):
    """
    Context manager that configures and installs the Scout plugin for Bottle.
    """
    # Enable Scout by default in tests.
    if config is None:
        config = {"scout.monitor": True}

    # Disable running the agent.
    config["scout.core_agent_launch"] = False

    app = Bottle()

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
    assert tracked_request.tags["path"] == "/home"
    assert tracked_request.tags["user_ip"] is None
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/home"


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
    with app_with_scout() as app:
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
    # With an empty config, "scout.monitor" defaults to False.
    with app_with_scout({}) as app:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert response.text == "Hello World!"
    assert tracked_requests == []


@mock.patch(
    "bottle.Request.remote_addr", new_callable=mock.PropertyMock, side_effect=ValueError
)
def test_remote_addr_exception(remote_addr, tracked_requests):
    """
    Scout doesn't crash if bottle.Request.remote_addr raises an exception.

    This cannot be tested without mocking because it should never happen.

    """
    with app_with_scout() as app:
        TestApp(app).get("/hello/")

    assert len(tracked_requests) == 1
    assert "user_ip" not in tracked_requests[0].tags
