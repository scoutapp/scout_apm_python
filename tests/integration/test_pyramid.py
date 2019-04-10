from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

import pytest
from webtest import TestApp

from scout_apm.api import Config

from .pyramid_app import app_configurator

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
        config = {"SCOUT_MONITOR": True}

    # Disable running the agent.
    config["SCOUT_CORE_AGENT_LAUNCH"] = False

    # Setup according to http://docs.scoutapm.com/#pyramid
    with app_configurator() as configurator:
        configurator.add_settings(**config)
        configurator.include("scout_apm.pyramid")
        app = configurator.make_wsgi_app()
    try:
        yield app
    finally:
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
        # Unlike most other frameworks, Pyramid doesn't catch all exceptions.
        with pytest.raises(ValueError):
            TestApp(app).get("/crash/", expect_errors=True)


def test_no_monitor():
    # With an empty config, "SCOUT_MONITOR" defaults to False.
    with app_with_scout({}) as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200


@patch(
    "pyramid.request.Request.remote_addr",
    new_callable=PropertyMock,
    side_effect=ValueError,
)
def test_remote_addr_exception(remote_addr):
    """
    Scout doesn't crash if pyramid.request.Request.remote_addr raises an exception.

    This cannot be tested without mocking because it should never happen.

    It's implemented in webob.request.Request and it's just a lookup in environ.

    """
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200
