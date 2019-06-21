# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

import falcon
import pytest
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.falcon import ScoutMiddleware
from tests.compat import mock


@contextmanager
def app_with_scout(config=None, middleware=None):
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
        middleware = []
    middleware.append(ScoutMiddleware(config=config))
    app = falcon.API(middleware=middleware)

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


@pytest.mark.parametrize(
    "frame_mocker",
    [
        # This checks the branch where stack inspection isn't possible, which
        # according to the inspect.currentframe() docs, is "some
        # implementations" of Python. For the record, it does work in
        # PyPy3.5-7.0.0:
        mock.patch("scout_apm.falcon.inspect.currentframe", return_value=None),
        # This checks the unlikely branch that somehow we can inspect the
        # current frame but not see the frame above it to find the "responder"
        # variable:
        mock.patch(
            "scout_apm.falcon.inspect.currentframe", return_value=mock.Mock(f_back=None)
        ),
        # This tests the future where Falcon is refactored so that 'responder'
        # is no longer the name for the responder method or it's not
        # visible in the frame above the middleware's process_response. Basically
        # if this line, or similar, are changed:
        # https://github.com/falconry/falcon/blob/7372895e0132fa7c626d9afde0d9e07e37655486/falcon/api.py#L247
        mock.patch(
            "scout_apm.falcon.inspect.currentframe",
            return_value=mock.Mock(f_back=mock.Mock(f_locals={})),
        ),
    ],
)
def test_home_stack_inspection_failures(frame_mocker, tracked_requests):
    with app_with_scout() as app, frame_mocker:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/tests.integration.test_falcon.HomeResource/GET"


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

    with app_with_scout(middleware=[ShortcutMiddleware()]) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Shortcut!"
    assert tracked_requests == []


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

    with app_with_scout(middleware=[ShortcutMiddleware()]) as app:
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
