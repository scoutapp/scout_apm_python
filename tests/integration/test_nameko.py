# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
from contextlib import contextmanager

import pytest
from nameko.containers import get_container_cls
from nameko.web.handlers import http
from webtest import TestApp
from werkzeug.wrappers import Response

from scout_apm.api import Config
from scout_apm.compat import datetime_to_timestamp, kwargs_only
from scout_apm.nameko import ScoutReporter
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)


@contextmanager
@kwargs_only
def app_with_scout(nameko_config=None, scout_config=None):
    """
    Context manager that yields a fresh Nameko WSGI app with Scout configured.
    """
    if scout_config is None:
        scout_config = {}

    scout_config["core_agent_launch"] = False
    scout_config.setdefault("monitor", True)
    Config.set(**scout_config)

    class Service(object):
        name = "myservice"

        scout = ScoutReporter()

        @http("GET", "/")
        def home(self, request):
            return "Welcome home."

        @http("GET", "/crash/")
        def crash(self, request):
            raise ValueError("BØØM!")  # non-ASCII

        @http("GET", "/return-error-response/")
        def return_error_response(self, request):
            return Response(status=503, response="Something went wrong")

        @http("GET", "/return-error-2tuple/")
        def return_error_2tuple(self, request):
            return (503, "Something went wrong")

        @http("GET", "/return-error-3tuple/")
        def return_error_3tuple(self, request):
            return (503, {}, "Something went wrong")

        @http("GET", "/return-error-badtuple/")
        def return_error_badtuple(self, request):
            return ("Nameko doesn't support one tuples",)

    if nameko_config is None:
        nameko_config = {}
    # Container setup copied from Nameko's container_factory pytest fixture,
    # which we don't use - see pytest.ini
    container_cls = get_container_cls(nameko_config)
    container = container_cls(Service, nameko_config)
    try:
        container.start()

        # A bit of introspection to look inside the container and pull out the WSGI
        # app
        app = list(container.subextensions)[0].get_wsgi_app()

        # N.B. We're sidestepping the Nameko testing conventions
        # (https://docs.nameko.io/en/stable/testing.html) to make our tests more
        # uniform between frameworks. See pytest.ini.

        yield app
    finally:
        container.kill()
        Config.reset_all()


def test_home(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/myservice.home"


def test_home_ignored(tracked_requests):
    with app_with_scout(scout_config={"ignore": ["/"]}) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert tracked_requests == []


@parametrize_filtered_params
def test_filtered_params(params, expected_path, tracked_requests):
    with app_with_scout() as app:
        TestApp(app).get("/", params=params)

    assert tracked_requests[0].tags["path"] == expected_path


@parametrize_user_ip_headers
def test_user_ip(headers, client_address, expected, tracked_requests):
    with app_with_scout() as app:
        TestApp(app).get(
            "/",
            headers=headers,
            extra_environ=(
                {str("REMOTE_ADDR"): client_address}
                if client_address is not None
                else {}
            ),
        )

    tracked_request = tracked_requests[0]
    assert tracked_request.tags["user_ip"] == expected


def test_user_ip_collection_disabled(tracked_requests):
    with app_with_scout(scout_config={"collect_remote_ip": False}) as app:
        TestApp(app).get(
            "/", extra_environ={str("REMOTE_ADDR"): str("1.1.1.1")},
        )

    tracked_request = tracked_requests[0]
    assert "user_ip" not in tracked_request.tags


@parametrize_queue_time_header_name
def test_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    with app_with_scout() as app:
        response = TestApp(app).get(
            "/", headers={header_name: str("t=") + str(queue_start)}
        )

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    assert isinstance(queue_time_ns, int) and queue_time_ns > 0


def test_amazon_queue_time(tracked_requests):
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow())) - 2
    with app_with_scout() as app:
        response = TestApp(app).get(
            "/",
            headers={
                "X-Amzn-Trace-Id": str(
                    "Self=1-{}-12456789abcdef012345678".format(queue_start)
                )
            },
        )

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    assert isinstance(queue_time_ns, int) and queue_time_ns > 0


def test_server_error(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/crash/", expect_errors=True)

    assert response.status_int == 500
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["error"] == "true"
    assert tracked_request.tags["path"] == "/crash/"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/myservice.crash"


@pytest.mark.parametrize(
    "url, transaction_name",
    [
        ["/return-error-response/", "return_error_response"],
        ["/return-error-2tuple/", "return_error_2tuple"],
        ["/return-error-3tuple/", "return_error_3tuple"],
    ],
)
def test_return_error(url, transaction_name, tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get(url, expect_errors=True)

    assert response.status_int == 503
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["error"] == "true"
    assert tracked_request.tags["path"] == url
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/myservice.{}".format(transaction_name)


def test_return_error_bad_tuple(tracked_requests):
    # Check that we don't cause the crash on a bad tuple shape
    with app_with_scout() as app:
        response = TestApp(app).get("/return-error-badtuple/", expect_errors=True)

    assert response.status_int == 500
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["error"] == "true"
    assert tracked_request.tags["path"] == "/return-error-badtuple/"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/myservice.return_error_badtuple"


def test_no_monitor(tracked_requests):
    with app_with_scout(scout_config={"monitor": False}) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert tracked_requests == []
