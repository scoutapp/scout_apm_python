# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager
from urllib.parse import urlencode

import pytest
from asgiref.testing import ApplicationCommunicator
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

import scout_apm.core
from scout_apm.api import Config
from scout_apm.async_.starlette import ScoutMiddleware
from tests.integration.util import parametrize_filtered_params
from tests.tools import async_test


@contextmanager
def app_with_scout(scout_config=None):
    """
    Context manager that configures and installs the Scout plugin for a basic
    Starlette application.
    """
    if scout_config is None:
        scout_config = {}

    scout_config["core_agent_launch"] = False
    scout_config.setdefault("monitor", True)
    Config.set(**scout_config)

    app = Starlette()

    @app.route("/")
    async def home(request):
        return PlainTextResponse("Welcome home.")

    @app.route("/hello/")
    async def hello(request):
        return PlainTextResponse("Hello World!")

    @app.route("/crash/")
    async def crash(request):
        raise ValueError("BØØM!")  # non-ASCII

    @app.exception_handler(500)
    async def error(request, exc):
        # Always raise exceptions
        raise exc

    scout_apm.core.install()
    # must be added last to be the outermost middleware
    app.add_middleware(ScoutMiddleware)

    try:
        yield app
    finally:
        Config.reset_all()


def get_scope(**kwargs):
    kwargs.setdefault("headers", [])
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "method": "GET",
        "query_string": b"",
        "server": ("testserver", 80),
        **kwargs,
    }


@async_test
async def test_home(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, get_scope(path="/"))
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/"
    span = tracked_request.complete_spans[0]
    assert (
        span.operation
        == "Controller/tests.integration.test_starlette_py36plus.app_with_scout.<locals>.home"
    )


@async_test
async def test_home_ignored(tracked_requests):
    with app_with_scout(scout_config={"ignore": ["/"]}) as app:
        communicator = ApplicationCommunicator(app, get_scope(path="/"))
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Welcome home."
    assert tracked_requests == []


@async_test
async def test_hello(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, get_scope(path="/hello/"))
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/hello/"
    span = tracked_request.complete_spans[0]
    assert (
        span.operation
        == "Controller/tests.integration.test_starlette_py36plus.app_with_scout.<locals>.hello"
    )


@parametrize_filtered_params
@async_test
async def test_filtered_params(params, expected_path, tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, get_scope(path="/", query_string=urlencode(params).encode("utf-8"))
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert tracked_requests[0].tags["path"] == expected_path


@async_test
async def test_server_error(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, get_scope(path="/crash/"))
        with pytest.raises(ValueError) as excinfo:
            await communicator.send_input({"type": "http.request"})
            await communicator.receive_output()

    assert excinfo.value.args == ("BØØM!",)
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/crash/"
    assert tracked_request.tags["error"] == "true"
    span = tracked_request.complete_spans[0]
    assert (
        span.operation
        == "Controller/tests.integration.test_starlette_py36plus.app_with_scout.<locals>.crash"
    )
