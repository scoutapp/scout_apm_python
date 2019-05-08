# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from webtest import TestApp

from scout_apm.api import Config
from scout_apm.bottle import ScoutPlugin

from .bottle_app import app

try:
    from unittest.mock import PropertyMock, patch
except ImportError:  # Python 2
    from mock import PropertyMock, patch


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

    # Save a reference to the original configuration and make changes in a copy.
    app_config = app.config.copy()

    # Setup according to https://docs.scoutapm.com/#bottle
    app.config.update(config)
    scout = ScoutPlugin()
    app.install(scout)
    try:
        yield app
    finally:
        # Restore original configuration and clear all caches.
        app.config = app_config
        app.reset()
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


def test_named():
    with app_with_scout() as app:
        response = TestApp(app).get("/named/")
        assert response.status_int == 200


def test_no_monitor():
    # With an empty config, "scout.monitor" defaults to False.
    with app_with_scout({}) as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200


@patch("bottle.Request.remote_addr", new_callable=PropertyMock, side_effect=ValueError)
def test_remote_addr_exception(remote_addr):
    """
    Scout doesn't crash if bottle.Request.remote_addr raises an exception.

    This cannot be tested without mocking because it should never happen.

    """
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200
