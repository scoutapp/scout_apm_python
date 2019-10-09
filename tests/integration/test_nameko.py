# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import sys
from contextlib import contextmanager

from nameko.containers import get_container_cls
from nameko.web.handlers import http
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.compat import datetime_to_timestamp
from scout_apm.nameko import ScoutReporter
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)


@contextmanager
def app_with_scout(nameko_config=None, scout_config=None):
    """
    Context manager that yields a fresh Nameko WSGI app with Scout configured.
    """
    if scout_config is None:
        scout_config = {"monitor": True}
    scout_config["core_agent_launch"] = False
    Config.set(**scout_config)

    # Nameko setup
    class Service(object):
        name = "myservice"

        scout = ScoutReporter()

        @http("GET", "/")
        def home(self, request):
            return "Welcome home."

        @http("GET", "/crash/")
        def crash(self, request):
            raise ValueError("BØØM!")  # non-ASCII

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
        # uniform between frameworks

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
    with app_with_scout(scout_config={"monitor": True, "ignore": ["/"]}) as app:
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
def test_user_ip(headers, extra_environ, expected, tracked_requests):
    if sys.version_info[0] == 2:
        # Required for WebTest lint
        headers = {str(k): str(v) for k, v in headers.items()}
        extra_environ = {str(k): str(v) for k, v in extra_environ.items()}

    with app_with_scout() as app:
        TestApp(app).get("/", headers=headers, extra_environ=extra_environ)

    tracked_request = tracked_requests[0]
    assert tracked_request.tags["user_ip"] == expected


@parametrize_queue_time_header_name
def test_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow()) - 2)
    with app_with_scout() as app:
        response = TestApp(app).get(
            "/", headers={header_name: str("t=") + str(queue_start)}
        )

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


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


def test_no_monitor(tracked_requests):
    with app_with_scout(scout_config={"monitor": False}) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert tracked_requests == []
