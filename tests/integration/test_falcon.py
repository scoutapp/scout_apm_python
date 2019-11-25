# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import logging
from contextlib import contextmanager

import falcon
import pytest
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.compat import datetime_to_timestamp, utc
from scout_apm.falcon import ScoutMiddleware
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)


@contextmanager
def app_with_scout(config=None, middleware=None, set_api=True):
    """
    Context manager that yields a fresh Falcon app with Scout configured.
    """
    # Enable Scout by default in tests.
    if config is None:
        config = {}

    config["core_agent_launch"] = False
    config.setdefault("monitor", True)

    if middleware is None:
        middleware = ["scout"]
    scout_index = middleware.index("scout")
    assert scout_index != -1
    scout_middleware = ScoutMiddleware(config=config)
    middleware[scout_index] = scout_middleware

    app = falcon.API(middleware=middleware)
    if set_api:
        scout_middleware.set_api(app)

    class HomeResource(object):
        def on_get(self, req, resp):
            resp.status = falcon.HTTP_200
            resp.content_type = falcon.MEDIA_TEXT
            resp.body = "Welcome home."

        def on_get_suffixed(self, req, resp):
            self.on_get(req, resp)
            resp.body = "Welcome home, suffixed."

    app.add_route("/", HomeResource())
    app.add_route("/suffixed", HomeResource(), suffix="suffixed")

    class CrashResource(object):
        def on_get(self, req, resp):
            raise ValueError("BØØM!")  # non-ASCII

    app.add_route("/crash", CrashResource())

    class ErrorResource(object):
        def on_get(self, req, resp):
            raise falcon.HTTPStatus("748 Confounded by ponies")

    app.add_route("/error", ErrorResource())

    class ReturnErrorResource(object):
        def on_get(self, req, resp):
            resp.status = "503 Something went wrong"
            resp.body = "Something went wrong"

    app.add_route("/return-error", ReturnErrorResource())

    class BadStatusResource(object):
        def on_get(self, req, resp):
            resp.status = "bad"

    app.add_route("/bad-status", BadStatusResource())

    try:
        yield app
    finally:
        Config.reset_all()


def test_set_api_wrong_type():
    scout_middleware = ScoutMiddleware(config={})

    with pytest.raises(ValueError) as excinfo:
        scout_middleware.set_api(None)

    assert str(excinfo.value) == "api should be an instance of falcon.API"


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
    assert (
        span.operation == "Controller/tests.integration.test_falcon.HomeResource.on_get"
    )


def test_home_without_set_api(caplog, tracked_requests):
    with app_with_scout(set_api=False) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/tests.integration.test_falcon.HomeResource.GET"
    falcon_log_tuples = [x for x in caplog.record_tuples if x[0] == "scout_apm.falcon"]
    assert falcon_log_tuples == [
        (
            "scout_apm.falcon",
            logging.WARNING,
            (
                "ScoutMiddleware.set_api() should be called before requests "
                "begin for more detail"
            ),
        )
    ]


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


def test_home_suffixed(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/suffixed")

    assert response.status_int == 200
    assert response.text == "Welcome home, suffixed."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/suffixed"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert (
        span.operation
        == "Controller/tests.integration.test_falcon.HomeResource.on_get_suffixed"
    )


def test_home_ignored(tracked_requests):
    with app_with_scout({"ignore": ["/"]}) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert tracked_requests == []


@parametrize_filtered_params
def test_filtered_params(params, expected_path, tracked_requests):
    with app_with_scout() as app:
        TestApp(app).get("/", params=params)

    assert tracked_requests[0].tags["path"] == expected_path


@parametrize_queue_time_header_name
def test_queue_time(header_name, tracked_requests):
    # Not testing floats due to Python 2/3 rounding differences
    queue_start = int(datetime_to_timestamp(dt.datetime.now(tz=utc))) - 2
    with app_with_scout() as app:
        response = TestApp(app).get(
            "/", headers={header_name: str("t=") + str(queue_start)}
        )

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    queue_time_ns = tracked_requests[0].tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


def test_amazon_queue_time(tracked_requests):
    queue_start = int(datetime_to_timestamp(dt.datetime.now(tz=utc))) - 2
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
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


def test_middleware_returning_early_from_process_request(tracked_requests):
    class ShortcutMiddleware(object):
        def process_request(self, req, resp):
            resp.status = falcon.HTTP_200
            resp.body = "Shortcut!"
            resp.complete = True

        def process_resource(self, req, resp, resource, params):
            pass

        def process_response(self, req, resp, resource, req_succeeded):
            pass

    with app_with_scout(middleware=[ShortcutMiddleware(), "scout"]) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Shortcut!"
    assert tracked_requests == []


def test_middleware_deleting_scout_tracked_request(tracked_requests):
    class AdversarialMiddleware(object):
        def process_request(self, req, resp):
            pass

        def process_resource(self, req, resp, resource, params):
            req.context.saved_scout_tracked_request = req.context.scout_tracked_request
            del req.context.scout_tracked_request

        def process_response(self, req, resp, resource, req_succeeded):
            pass

    class AdversarialUndoMiddleware(object):
        def process_request(self, req, resp):
            pass

        def process_resource(self, req, resp, resource, params):
            req.context.scout_tracked_request = req.context.saved_scout_tracked_request
            del req.context.saved_scout_tracked_request

        def process_response(self, req, resp, resource, req_succeeded):
            pass

    with app_with_scout(
        middleware=[AdversarialMiddleware(), "scout", AdversarialUndoMiddleware()]
    ) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.active_spans == []
    assert tracked_request.complete_spans == []


def test_middleware_returning_early_from_process_resource(tracked_requests):
    class ShortcutMiddleware(object):
        def process_request(self, req, resp):
            pass

        def process_resource(self, req, resp, resource, params):
            resp.status = falcon.HTTP_200
            resp.body = "Shortcut!"
            resp.complete = True

        def process_response(self, req, resp, resource, req_succeeded):
            pass

    with app_with_scout(middleware=[ShortcutMiddleware(), "scout"]) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Shortcut!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.active_spans == []
    assert tracked_request.complete_spans == []


def test_not_found(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/not-found", expect_errors=True)

    assert response.status_int == 404
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/not-found"
    assert tracked_request.tags["error"] == "true"
    assert tracked_request.active_spans == []
    assert tracked_request.complete_spans == []


def test_crash(tracked_requests):
    with app_with_scout() as app, pytest.raises(ValueError) as excinfo:
        # Falcon doesn't do error responses itself for uncaught exceptions,
        # instead relying on the host WSGI server to do this.
        TestApp(app).get("/crash")

    assert excinfo.value.args == ("BØØM!",)
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/crash"
    assert tracked_request.tags["error"] == "true"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert (
        span.operation
        == "Controller/tests.integration.test_falcon.CrashResource.on_get"
    )


def test_error(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/error", expect_errors=True)

    assert response.status_int == 748
    assert response.text == ""
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/error"
    assert tracked_request.tags["error"] == "true"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert (
        span.operation
        == "Controller/tests.integration.test_falcon.ErrorResource.on_get"
    )


def test_return_error(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/return-error", expect_errors=True)

    assert response.status_int == 503
    assert response.text == "Something went wrong"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/return-error"
    assert tracked_request.tags["error"] == "true"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert (
        span.operation
        == "Controller/tests.integration.test_falcon.ReturnErrorResource.on_get"
    )


def test_bad_status(tracked_requests):
    with app_with_scout() as app, pytest.raises(AssertionError) as excinfo:
        TestApp(app).get("/bad-status", expect_errors=True)

    assert isinstance(excinfo.value, AssertionError)
    assert "should be a three-digit integer" in str(excinfo.value)
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/bad-status"
    assert tracked_request.tags["error"] == "true"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert (
        span.operation
        == "Controller/tests.integration.test_falcon.BadStatusResource.on_get"
    )
