# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import functools
from contextlib import contextmanager

import asgiref.sync
import pytest
from asgiref.testing import ApplicationCommunicator

import scout_apm.core
from scout_apm.api import Config
from scout_apm.asgi import wrap_asgi_application


@contextmanager
def app_with_scout(scout_config=None):
    """
    Context manager that configures and installs the Scout plugin for a basic
    ASGI (3) application.
    """
    if scout_config is None:
        scout_config = {}

    # config["SCOUT_CORE_AGENT_LAUNCH"] = False
    # config.setdefault("SCOUT_MONITOR", True)
    # Disable Flask's error page to improve debugging
    # config.setdefault("PROPAGATE_EXCEPTIONS", True)
    Config.set(**scout_config)

    scout_apm.core.install()

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        body = await receive()
        assert body["type"] == "http.request"
        if scope["path"] == "/":
            body = b"Welcome home."
        elif scope["path"] == "/hello/":
            body = b"Hello World!"
        elif scope["path"] == "/crash/":
            raise ValueError("BØØM!")  # non-ASCII

        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": body, "more_body": False})

    wrapped_app = wrap_asgi_application(app)

    try:
        yield wrapped_app
    finally:
        Config.reset_all()


def async_to_sync(func):
    """
    Wrap async_to_sync with another function because Pytest complains about
    collecting the resulting callable object as a test because it's not a true
    function:

    PytestCollectionWarning: cannot collect 'test_foo' because it is not a
    function.
    """
    sync_func = asgiref.sync.async_to_sync(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return sync_func(*args, **kwargs)

    return wrapper


def get_scope(**kwargs):
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "method": "GET",
        "query_string": b"",
        "server": ("testserver", 80),
        **kwargs,
    }


@async_to_sync
async def test_home(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, get_scope(path="/"))
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        assert response_start["type"] == "http.response.start"
        assert response_start["status"] == 200
        assert response_start["headers"] == []
        response_body = await communicator.receive_output()
        assert response_body["type"] == "http.response.body"
        assert response_body["body"] == b"Welcome home."

    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/"
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/GET_/"


@async_to_sync
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
    assert span.operation == "Controller/GET_/crash/"
