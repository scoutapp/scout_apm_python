# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
from urllib.parse import urlencode

import django
import pytest
from asgiref.sync import sync_to_async
from asgiref.testing import ApplicationCommunicator

from scout_apm.compat import datetime_to_timestamp
from scout_apm.django.instruments.channels import ensure_instrumented
from tests.compat import mock
from tests.integration.test_django import app_with_scout as django_app_with_scout
from tests.integration.test_django import make_admin_user
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)
from tests.tools import asgi_http_scope, asgi_websocket_scope, async_test


class app_with_scout:
    """
    An async context manager to construct since django_app_with_scout needs to
    perform queries in 'migrate' on first use.

    Would use contextlib.asynccontextmanager but that's Python 3.7+ and we
    support 3.5+ at time of writing.
    """

    def __init__(self, **settings):
        self.settings = settings

    async def __aenter__(self):
        try:
            import channels  # noqa
        except ImportError:
            pytest.skip("No Channels")

        self.app_instance = django_app_with_scout(**self.settings)
        await sync_to_async(self.app_instance.__enter__)()

        # Import after Django setup
        from channels.auth import AuthMiddlewareStack
        from channels.http import AsgiHandler
        from channels.generic.http import AsyncHttpConsumer
        from channels.generic.websocket import WebsocketConsumer
        from channels.routing import URLRouter

        class BasicHttpConsumer(AsyncHttpConsumer):
            async def handle(self, body):
                await self.send_response(
                    200,
                    b"Hello world, asynchronously!",
                    headers=[(b"Content-Type", b"text/plain")],
                )

        class BasicWebsocketConsumer(WebsocketConsumer):
            def connect(self):
                self.accept()

            def receive(self, text_data=None, bytes_data=None):
                self.send(text_data="Hello world!")

        if django.VERSION >= (2, 0):
            from django.urls import path

            router = URLRouter(
                [
                    path("basic-http/", BasicHttpConsumer),
                    path("basic-ws/", BasicWebsocketConsumer),
                    path("", AsgiHandler),
                ]
            )
        else:
            from django.conf.urls import url

            router = URLRouter(
                [
                    url(r"^basic-http/$", BasicHttpConsumer),
                    url(r"^basic-ws/$", BasicWebsocketConsumer),
                    url(r"^$", AsgiHandler),
                ]
            )

        return AuthMiddlewareStack(router)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await sync_to_async(self.app_instance.__exit__)(exc_type, exc_val, exc_tb)


def create_logged_in_session(user):
    from django.contrib.auth import login
    from django.contrib.sessions.backends.db import SessionStore

    session = SessionStore()
    session.create()
    # django.contrib.auth.login needs a request, so fake one
    fake_request = mock.Mock(session=session)
    login(fake_request, user)
    session.save()
    return session


@async_test
async def test_instruments_idempotent():
    """
    Check second call doesn't crash (should be a no-op)
    """
    async with app_with_scout():
        ensure_instrumented()


@async_test
async def test_vanilla_view_asgi_handler(tracked_requests):
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(app, asgi_http_scope(path="/"))
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.tags["user_ip"] is None
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.django_app.home",
        "Middleware",
    ]


@async_test
async def test_http_consumer(tracked_requests):
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/basic-http/")
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Hello world, asynchronously!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/basic-http/"
    span = tracked_request.complete_spans[0]
    assert span.operation == (
        "Controller/tests.integration.test_django_channels_py36plus."
        + "app_with_scout.__aenter__.<locals>.BasicHttpConsumer.http_request"
    )


@async_test
async def test_http_consumer_large_body(tracked_requests):
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/basic-http/")
        )
        await communicator.send_input({"type": "http.request", "more_body": True})
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert len(tracked_requests) == 1


@parametrize_filtered_params
@async_test
async def test_http_consumer_filtered_params(params, expected_path, tracked_requests):
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_http_scope(
                path="/basic-http/", query_string=urlencode(params).encode("utf-8")
            ),
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert tracked_requests[0].tags["path"] == "/basic-http" + expected_path


@async_test
async def test_http_consumer_ignore(tracked_requests):
    async with app_with_scout(SCOUT_IGNORE="/basic-http/") as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/basic-http/")
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert tracked_requests == []


@parametrize_user_ip_headers
@async_test
async def test_http_consumer_user_ip(
    headers, client_address, expected, tracked_requests
):
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_http_scope(
                path="/basic-http/", headers=headers, client=(client_address, None)
            ),
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert tracked_requests[0].tags["user_ip"] == expected


@parametrize_queue_time_header_name
@async_test
async def test_http_consumer_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_http_scope(
                path="/basic-http/",
                headers={header_name: str("t=") + str(queue_start)},
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
async def test_http_consumer_username(tracked_requests):
    async with app_with_scout() as app:
        from django.conf.global_settings import SESSION_COOKIE_NAME
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def make_user_and_session():
            admin_user = make_admin_user()
            session = create_logged_in_session(admin_user)
            return admin_user, session

        admin_user, session = await make_user_and_session()

        scope = asgi_http_scope(
            path="/basic-http/",
            headers={
                "cookie": "{}={}".format(SESSION_COOKIE_NAME, session.session_key)
            },
        )
        communicator = ApplicationCommunicator(app, scope)
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["username"] == admin_user.username


@async_test
async def test_http_consumer_username_exception(tracked_requests):
    async with app_with_scout() as app:
        mock_user = mock.Mock()
        mock_user.get_username.side_effect = ValueError

        scope = asgi_http_scope(path="/basic-http/", user=mock_user)
        communicator = ApplicationCommunicator(app, scope)
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert "username" not in tracked_requests[0].tags


@async_test
async def test_websocket_consumer_connect(tracked_requests):
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, asgi_websocket_scope(path="/basic-ws/")
        )
        await communicator.send_input({"type": "websocket.connect"})
        response = await communicator.receive_output()
        await communicator.wait(timeout=0.001)

    assert response["type"] == "websocket.accept"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/basic-ws/"
    span = tracked_request.complete_spans[0]
    assert span.operation == (
        "Controller/tests.integration.test_django_channels_py36plus."
        + "app_with_scout.__aenter__.<locals>.BasicWebsocketConsumer.websocket_connect"
    )


@parametrize_filtered_params
@async_test
async def test_websocket_consumer_connect_filtered_params(
    params, expected_path, tracked_requests
):
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_websocket_scope(
                path="/basic-ws/", query_string=urlencode(params).encode("utf-8")
            ),
        )
        await communicator.send_input({"type": "websocket.connect"})
        response = await communicator.receive_output()
        await communicator.wait(timeout=0.001)

    assert response["type"] == "websocket.accept"
    assert tracked_requests[0].tags["path"] == "/basic-ws" + expected_path


@async_test
async def test_websocket_consumer_ignore(tracked_requests):
    async with app_with_scout(SCOUT_IGNORE="/basic-ws/") as app:
        communicator = ApplicationCommunicator(
            app, asgi_websocket_scope(path="/basic-ws/")
        )
        await communicator.send_input({"type": "websocket.connect"})
        response = await communicator.receive_output()
        await communicator.wait(timeout=0.001)

    assert response["type"] == "websocket.accept"
    assert tracked_requests == []


@parametrize_user_ip_headers
@async_test
async def test_websocket_consumer_connect_user_ip(
    headers, client_address, expected, tracked_requests
):
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_websocket_scope(
                path="/basic-ws/", headers=headers, client=(client_address, None)
            ),
        )
        await communicator.send_input({"type": "websocket.connect"})
        response = await communicator.receive_output()
        await communicator.wait(timeout=0.001)

    assert response["type"] == "websocket.accept"
    assert tracked_requests[0].tags["user_ip"] == expected


@parametrize_queue_time_header_name
@async_test
async def test_websocket_consumer_connect_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    async with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_websocket_scope(
                path="/basic-ws/", headers={header_name: str("t=") + str(queue_start)},
            ),
        )
        await communicator.send_input({"type": "websocket.connect"})
        response = await communicator.receive_output()
        await communicator.wait(timeout=0.001)

    assert response["type"] == "websocket.accept"
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


@async_test
async def test_websocket_consumer_connect_username(tracked_requests):
    async with app_with_scout() as app:
        from django.conf.global_settings import SESSION_COOKIE_NAME
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def make_user_and_session():
            admin_user = make_admin_user()
            session = create_logged_in_session(admin_user)
            return admin_user, session

        admin_user, session = await make_user_and_session()
        scope = asgi_websocket_scope(
            path="/basic-ws/",
            headers={
                "cookie": "{}={}".format(SESSION_COOKIE_NAME, session.session_key)
            },
        )
        communicator = ApplicationCommunicator(app, scope)
        await communicator.send_input({"type": "websocket.connect"})
        response = await communicator.receive_output()
        await communicator.wait(timeout=0.001)

    assert response["type"] == "websocket.accept"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["username"] == admin_user.username


@async_test
async def test_websocket_consumer_connect_username_exception(tracked_requests):
    async with app_with_scout() as app:
        mock_user = mock.Mock()
        mock_user.get_username.side_effect = ValueError

        scope = asgi_websocket_scope(path="/basic-ws/", user=mock_user)
        communicator = ApplicationCommunicator(app, scope)
        await communicator.send_input({"type": "websocket.connect"})
        response = await communicator.receive_output()
        await communicator.wait(timeout=0.001)

    assert response["type"] == "websocket.accept"
    assert "username" not in tracked_requests[0].tags
