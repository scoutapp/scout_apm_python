# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sys
from contextlib import contextmanager

import falcon
import pytest
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.falcon import ScoutMiddleware
from tests.integration.util import parametrize_user_ip_headers


@contextmanager
def app_with_scout(config=None, middleware=None, set_api=True):
    """
    Context manager that yields a fresh Falcon app with Scout configured.
    """
    # Enable Scout by default in tests.
    if config is None:
        config = {"monitor": True}

    # Disable running the agent.
    config["core_agent_launch"] = False

    # Basic Falcon app
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
            raise falcon.HTTPStatus("748 Confounded by ponies")

    app.add_route("/crash", CrashResource())

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
def test_user_ip(headers, extra_environ, expected, tracked_requests):
    if sys.version_info[0] == 2:
        # Required for WebTest lint
        headers = {str(k): str(v) for k, v in headers.items()}
        extra_environ = {str(k): str(v) for k, v in extra_environ.items()}

    with app_with_scout() as app:
        TestApp(app).get("/", headers=headers, extra_environ=extra_environ)

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
    with app_with_scout({"monitor": True, "ignore": ["/"]}) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert tracked_requests == []


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
    with app_with_scout() as app:
        response = TestApp(app).get("/crash", expect_errors=True)

    assert response.status_int == 748
    assert response.text == ""
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
