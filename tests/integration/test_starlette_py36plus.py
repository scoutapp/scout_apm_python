# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
from contextlib import contextmanager
from urllib.parse import urlencode

import pytest
from asgiref.testing import ApplicationCommunicator
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse

import scout_apm.core
from scout_apm.api import Config
from scout_apm.async_.starlette import ScoutMiddleware
from scout_apm.compat import datetime_to_timestamp
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)
from tests.tools import async_test


@contextmanager
def app_with_scout(*, scout_config=None):
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
    class HelloEndpoint(HTTPEndpoint):
        async def get(self, request):
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


def get_scope(headers=None, **kwargs):
    if headers is None:
        headers = {}
    headers = [
        [k.lower().encode("latin-1"), v.encode("latin-1")] for k, v in headers.items()
    ]
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "method": "GET",
        "query_string": b"",
        "server": ("testserver", 80),
        "headers": headers,
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
        == "Controller/tests.integration.test_starlette_py36plus.app_with_scout.<locals>.HelloEndpoint"
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


@parametrize_user_ip_headers
@async_test
async def test_user_ip(headers, client_address, expected, tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, get_scope(path="/", headers=headers, client=(client_address, None))
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["user_ip"] == expected


@parametrize_queue_time_header_name
@async_test
async def test_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            get_scope(path="/", headers={header_name: str("t=") + str(queue_start)}),
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


@async_test
async def test_amazon_queue_time(tracked_requests):
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            get_scope(
                path="/",
                headers={
                    "X-Amzn-Trace-Id": "Self=1-{}-12456789abcdef012345678".format(
                        queue_start
                    )
                },
            ),
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


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


@async_test
async def test_no_monitor(tracked_requests):
    with app_with_scout(scout_config={"monitor": False}) as app:
        communicator = ApplicationCommunicator(app, get_scope(path="/"))
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert tracked_requests == []


@async_test
async def test_unknown_asgi_scope(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, {"type": "lifespan"})
        await communicator.send_input({"type": "lifespan.startup"})
        response_start = await communicator.receive_output()

    assert response_start == {"type": "lifespan.startup.complete"}
    assert tracked_requests == []
