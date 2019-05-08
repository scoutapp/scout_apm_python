# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from webtest import TestApp

from scout_apm.api import Config
from scout_apm.flask import ScoutApm

from .flask_app import app

try:
    from unittest.mock import patch
except ImportError:  # Python 2.7
    from mock import patch


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

    # Setup according to https://docs.scoutapm.com/#flask
    scout = ScoutApm(app)
    for key, value in config.items():
        app.config[key] = value
    try:
        yield app
    finally:
        # Restore original configuration.
        assert app.before_first_request_funcs == [scout.before_first_request]
        assert app.before_request_funcs == {None: [scout.process_request]}
        assert app.after_request_funcs == {None: [scout.process_response]}
        assert app.dispatch_request == scout.dispatch_request
        del app.before_first_request_funcs[:]
        del app.before_request_funcs[None][:]
        del app.after_request_funcs[None][:]
        del app.dispatch_request
        # Reset Scout configuration.
        Config.reset_all()


def test_home():
    with app_with_scout() as app:
        response = TestApp(app).get("/")
        assert response.status_int == 200


def test_hello():
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200


def test_not_found():
    with app_with_scout() as app:
        response = TestApp(app).get("/not-found/", expect_errors=True)
        assert response.status_int == 404


def test_server_error():
    with app_with_scout() as app:
        response = TestApp(app).get("/crash/", expect_errors=True)
        assert response.status_int == 500


def test_options():
    with app_with_scout() as app:
        response = TestApp(app).options("/hello/")
        assert response.status_int == 200


def test_no_monitor():
    # With an empty config, "SCOUT_MONITOR" defaults to False.
    with app_with_scout({}) as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200


@patch("scout_apm.core.monkey.CallableProxy", side_effect=ValueError)
def test_wrapping_exception(CallableProxy):
    """
    Scout doesn't crash if scout_apm.core.monkey.CallableProxy raises an exception.

    This cannot be tested without mocking because it should never happen.

    """
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200
