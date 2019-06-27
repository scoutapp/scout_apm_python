# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from contextlib import contextmanager

import pytest
from pyramid.config import Configurator
from pyramid.response import Response
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.core.tracked_request import TrackedRequest
from tests.compat import mock
from tests.integration.util import parametrize_user_ip_headers


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

    def home(request):
        return Response("Welcome home.")

    def hello(request):
        return Response("Hello World!")

    def crash(request):
        raise ValueError("BØØM!")  # non-ASCII

    with Configurator() as configurator:
        configurator.add_route("home", "/")
        configurator.add_view(home, route_name="home", request_method="GET")
        configurator.add_route("hello", "/hello/")
        configurator.add_view(hello, route_name="hello")
        configurator.add_route("crash", "/crash/")
        configurator.add_view(crash, route_name="crash")

        # Setup according to https://docs.scoutapm.com/#pyramid
        configurator.add_settings(**config)
        configurator.include("scout_apm.pyramid")
        app = configurator.make_wsgi_app()

    try:
        yield app
    finally:
        # Reset Scout configuration.
        Config.reset_all()


def test_home(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/", expect_errors=True)

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.tags["user_ip"] is None
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/home"


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


def test_user_ip_exception(tracked_requests):
    """
    Scout doesn't crash if pyramid.request.Request.remote_addr raises an exception.

    This cannot be tested without mocking because it should never happen.

    It's implemented in webob.request.Request and it's just a lookup in environ.
    """
    remote_addr_patcher = mock.patch(
        "pyramid.request.Request.remote_addr",
        new_callable=mock.PropertyMock,
        side_effect=ValueError,
    )

    with app_with_scout() as app, remote_addr_patcher:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert "user_ip" not in tracked_requests[0].tags


def test_home_ignored(tracked_requests):
    with app_with_scout({"SCOUT_MONITOR": True, "SCOUT_IGNORE": ["/"]}) as app:
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
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/hello"


def test_not_found(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/not-found/", expect_errors=True)

    assert response.status_int == 404
    assert tracked_requests == []
    assert TrackedRequest._thread_lookup.instance is None


def test_server_error(tracked_requests):
    # Unlike most other frameworks, Pyramid doesn't catch all exceptions.
    with app_with_scout() as app, pytest.raises(ValueError):
        TestApp(app).get("/crash/", expect_errors=True)

    assert tracked_requests == []
    assert TrackedRequest._thread_lookup.instance is None


def test_no_monitor(tracked_requests):
    # With an empty config, "SCOUT_MONITOR" defaults to False.
    with app_with_scout({}) as app:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert tracked_requests == []
