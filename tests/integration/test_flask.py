# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

import pytest
from flask import Flask
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.flask import ScoutApm
from tests.compat import mock


@contextmanager
def app_with_scout(config=None):
    """
    Context manager that configures and installs the Scout plugin for Bottle.

    """
    # Enable Scout by default in tests.
    if config is None:
        config = {"SCOUT_MONITOR": True}

    # Disable running the agent.
    config["SCOUT_CORE_AGENT_LAUNCH"] = False

    # Basic Flask app
    app = Flask("test_app")

    @app.route("/")
    def home():
        return "Welcome home."

    @app.route("/hello/")
    def hello():
        return "Hello World!"

    @app.route("/crash/")
    def crash():
        raise ValueError("BØØM!")  # non-ASCII

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

    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.test_flask.home"
    ]


def test_hello(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200

    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.test_flask.hello"
    ]


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
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.test_flask.crash"
    ]


def test_automatic_options(tracked_requests):
    """
    We don't want to capture automatic options
    """
    with app_with_scout() as app:
        response = TestApp(app).options("/hello/")
        assert response.status_int == 200

    assert tracked_requests == []


@pytest.mark.xfail(reason="Integration still captures requests with monitor=False")
def test_no_monitor(tracked_requests):
    # With an empty config, "SCOUT_MONITOR" defaults to False.
    with app_with_scout({}) as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200

    assert tracked_requests == []


@mock.patch("scout_apm.core.monkey.CallableProxy", side_effect=ValueError)
def test_wrapping_exception(CallableProxy, tracked_requests):
    """
    Scout doesn't crash if scout_apm.core.monkey.CallableProxy raises an exception.

    This cannot be tested without mocking because it should never happen.

    """
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200

    assert tracked_requests == []
