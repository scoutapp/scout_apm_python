# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
from contextlib import contextmanager
from urllib.parse import urlencode

import pytest
from asgiref.testing import ApplicationCommunicator
from starlette.applications import Starlette
from starlette.authentication import AuthCredentials, AuthenticationBackend, SimpleUser
from starlette.background import BackgroundTasks
from starlette.endpoints import HTTPEndpoint
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from scout_apm.api import Config
from scout_apm.async_.starlette import ScoutMiddleware
from scout_apm.compat import datetime_to_timestamp
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)
from tests.tools import asgi_http_scope, async_test


@contextmanager
def app_with_scout(*, middleware=None, scout_config=None):
    """
    Context manager that configures and installs the Scout plugin for a basic
    Starlette application.
    """
    if scout_config is None:
        scout_config = {}

    scout_config["core_agent_launch"] = False
    scout_config.setdefault("monitor", True)

    async def home(request):
        return PlainTextResponse("Welcome home.")

    def sync_home(request):
        return PlainTextResponse("Welcome home, synchronously.")

    class HelloEndpoint(HTTPEndpoint):
        async def get(self, request):
            return PlainTextResponse("Hello World!")

    class SyncHelloEndpoint(HTTPEndpoint):
        def get(self, request):
            return PlainTextResponse("Hello Synchronous World!")

    async def crash(request):
        raise ValueError("BØØM!")  # non-ASCII

    async def return_error(request):
        return PlainTextResponse("Something went wrong", status_code=503)

    async def background_jobs(request):
        def sync_noop():
            pass

        async def async_noop():
            pass

        tasks = BackgroundTasks()
        tasks.add_task(sync_noop)
        tasks.add_task(async_noop)

        return PlainTextResponse("Triggering background jobs", background=tasks)

    class InstanceApp:
        async def __call__(self, scope, receive, send):
            resp = PlainTextResponse(
                "Welcome home from an app that's a class instance."
            )
            await resp(scope, receive, send)

    routes = [
        Route("/", endpoint=home),
        Route("/sync-home/", endpoint=sync_home),
        Route("/hello/", endpoint=HelloEndpoint),
        Route("/sync-hello/", endpoint=SyncHelloEndpoint),
        Route("/crash/", endpoint=crash),
        Route("/return-error/", endpoint=return_error),
        Route("/background-jobs/", endpoint=background_jobs),
        Route("/instance-app/", endpoint=InstanceApp()),
    ]

    async def raise_error_handler(request, exc):
        # Always raise exceptions
        raise exc

    if middleware is None:
        middleware = []

    # As per http://docs.scoutapm.com/#starlette
    Config.set(**scout_config)
    middleware.insert(0, Middleware(ScoutMiddleware))

    app = Starlette(
        routes=routes,
        middleware=middleware,
        exception_handlers={500: raise_error_handler},
    )

    try:
        yield app
    finally:
        Config.reset_all()


@async_test
async def test_home(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/"))
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
    assert span.operation == (
        "Controller/tests.integration.test_starlette_py36plus."
        + "app_with_scout.<locals>.home"
    )


@async_test
async def test_sync_home(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/sync-home/"))
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Welcome home, synchronously."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/sync-home/"
    span = tracked_request.complete_spans[0]
    assert span.operation == (
        "Controller/tests.integration.test_starlette_py36plus."
        + "app_with_scout.<locals>.sync_home"
    )


@async_test
async def test_home_ignored(tracked_requests):
    with app_with_scout(scout_config={"ignore": ["/"]}) as app:
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/"))
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
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/hello/"))
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
    assert span.operation == (
        "Controller/tests.integration.test_starlette_py36plus."
        + "app_with_scout.<locals>.HelloEndpoint"
    )


@async_test
async def test_sync_hello(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/sync-hello/")
        )
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Hello Synchronous World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/sync-hello/"
    span = tracked_request.complete_spans[0]
    assert span.operation == (
        "Controller/tests.integration.test_starlette_py36plus."
        + "app_with_scout.<locals>.SyncHelloEndpoint"
    )


@async_test
async def test_not_found(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/not-found/"))
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 404
    assert tracked_requests == []


@parametrize_filtered_params
@async_test
async def test_filtered_params(params, expected_path, tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_http_scope(path="/", query_string=urlencode(params).encode("utf-8")),
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
            app,
            asgi_http_scope(path="/", headers=headers, client=(client_address, None)),
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert tracked_requests[0].tags["user_ip"] == expected


@async_test
async def test_user_ip_collection_disabled(tracked_requests):
    with app_with_scout(scout_config={"collect_remote_ip": False}) as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/", client=("1.1.1.1", None))
        )
        await communicator.send_input({"type": "http.request"})
        await communicator.receive_output()
        await communicator.receive_output()

    tracked_request = tracked_requests[0]
    assert "user_ip" not in tracked_request.tags


@parametrize_queue_time_header_name
@async_test
async def test_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_http_scope(
                path="/", headers={header_name: str("t=") + str(queue_start)}
            ),
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    assert isinstance(queue_time_ns, int) and queue_time_ns > 0


@async_test
async def test_amazon_queue_time(tracked_requests):
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_http_scope(
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
    assert isinstance(queue_time_ns, int) and queue_time_ns > 0


@async_test
async def test_server_error(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/crash/"))
        await communicator.send_input({"type": "http.request"})
        with pytest.raises(ValueError) as excinfo:
            await communicator.receive_output()

    assert excinfo.value.args == ("BØØM!",)
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/crash/"
    assert tracked_request.tags["error"] == "true"
    span = tracked_request.complete_spans[0]
    assert span.operation == (
        "Controller/tests.integration.test_starlette_py36plus."
        + "app_with_scout.<locals>.crash"
    )


@async_test
async def test_return_error(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/return-error/")
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 503
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/return-error/"
    assert tracked_request.tags["error"] == "true"


@async_test
async def test_no_monitor(tracked_requests):
    with app_with_scout(scout_config={"monitor": False}) as app:
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/"))
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


@async_test
async def test_background_jobs(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/background-jobs/")
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()
        await communicator.wait()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["body"] == b"Triggering background jobs"
    assert len(tracked_requests) == 3

    sync_tracked_request = tracked_requests[1]
    assert len(sync_tracked_request.complete_spans) == 1
    sync_span = sync_tracked_request.complete_spans[0]
    assert sync_span.operation == (
        "Job/tests.integration.test_starlette_py36plus."
        + "app_with_scout.<locals>.background_jobs.<locals>.sync_noop"
    )

    async_tracked_request = tracked_requests[2]
    assert len(async_tracked_request.complete_spans) == 1
    async_span = async_tracked_request.complete_spans[0]
    assert async_span.operation == (
        "Job/tests.integration.test_starlette_py36plus."
        + "app_with_scout.<locals>.background_jobs.<locals>.async_noop"
    )


@async_test
async def test_username(tracked_requests):
    class DummyBackend(AuthenticationBackend):
        async def authenticate(self, request):
            return AuthCredentials(), SimpleUser("dummy")

    middleware = [Middleware(AuthenticationMiddleware, backend=DummyBackend())]

    with app_with_scout(middleware=middleware) as app:
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/"))
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["username"] == "dummy"


@async_test
async def test_username_bad_user(tracked_requests):
    class BadUserBackend(AuthenticationBackend):
        async def authenticate(self, request):
            return AuthCredentials(), object()

    middleware = [Middleware(AuthenticationMiddleware, backend=BadUserBackend())]

    with app_with_scout(middleware=middleware) as app:
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/"))
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert "username" not in tracked_request.tags


@async_test
async def test_instance_app(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/instance-app/")
        )
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Welcome home from an app that's a class instance."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/instance-app/"
    span = tracked_request.complete_spans[0]
    assert span.operation == (
        "Controller/tests.integration.test_starlette_py36plus."
        + "app_with_scout.<locals>.InstanceApp"
    )
