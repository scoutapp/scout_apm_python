# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
from contextlib import contextmanager
from urllib.parse import urlencode

import django
import pytest
from asgiref.testing import ApplicationCommunicator

from scout_apm.compat import datetime_to_timestamp
from tests.integration.test_django import app_with_scout as django_app_with_scout
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)
from tests.tools import asgi_http_scope, async_test

try:
    import channels
except ImportError:
    channels = None


skip_unless_channels = pytest.mark.skipif(
    channels is None, reason="Channels is required."
)


@contextmanager
def app_with_scout(**settings):
    """
    Set up the Django app and then add a Channels ASGI application on top.
    """
    with django_app_with_scout(**settings):
        from channels.http import AsgiHandler
        from channels.generic.http import AsyncHttpConsumer
        from channels.routing import URLRouter

        class BasicHttpConsumer(AsyncHttpConsumer):
            async def handle(self, body):
                await self.send_response(
                    200,
                    b"Hello world, asynchronously!",
                    headers=[(b"Content-Type", b"text/plain")],
                )

        if django.VERSION >= (2, 0):
            from django.urls import path

            application = URLRouter(
                [path("channels-basic/", BasicHttpConsumer), path("", AsgiHandler)]
            )
        else:
            from django.conf.urls import url

            application = URLRouter(
                [url(r"^channels-basic/$", BasicHttpConsumer), url(r"^$", AsgiHandler)]
            )

        yield application


@skip_unless_channels
@async_test
async def test_normal_django_view(tracked_requests):
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
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.tags["user_ip"] is None
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.django_app.home",
        "Middleware",
    ]


@skip_unless_channels
@async_test
async def test_async_http_consumer(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/channels-basic/")
        )
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Hello world, asynchronously!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/channels-basic/"
    span = tracked_request.complete_spans[0]
    assert span.operation == (
        "Controller/tests.integration.test_django_channels_py36plus."
        + "app_with_scout.<locals>.BasicHttpConsumer"
    )


@skip_unless_channels
@async_test
async def test_async_http_consumer_large_body(tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/channels-basic/")
        )
        await communicator.send_input({"type": "http.request", "more_body": True})
        await communicator.send_input({"type": "http.request"})
        # Read the response.
        response_start = await communicator.receive_output()
        response_body = await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert len(tracked_requests) == 1


@parametrize_filtered_params
@async_test
async def test_filtered_params(params, expected_path, tracked_requests):
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_http_scope(
                path="/channels-basic/", query_string=urlencode(params).encode("utf-8")
            ),
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert tracked_requests[0].tags["path"] == "/channels-basic" + expected_path


@skip_unless_channels
@async_test
async def test_ignore(tracked_requests):
    with app_with_scout(SCOUT_IGNORE="/channels-basic/") as app:
        communicator = ApplicationCommunicator(
            app, asgi_http_scope(path="/channels-basic/")
        )
        await communicator.send_input({"type": "http.request"})
        response_start = await communicator.receive_output()
        await communicator.receive_output()

    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert tracked_requests == []


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


@parametrize_queue_time_header_name
@async_test
async def test_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    with app_with_scout() as app:
        communicator = ApplicationCommunicator(
            app,
            asgi_http_scope(
                path="/channels-basic/",
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
