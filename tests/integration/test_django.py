# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path
from contextlib import contextmanager

import django
import pytest
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.test.utils import modify_settings, override_settings
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.core.tracked_request import TrackedRequest

from .django_app import app as app_unused  # noqa: F401

try:
    from unittest.mock import Mock, patch
except ImportError:  # Python 2
    from mock import Mock, patch


skip_unless_new_style_middleware = pytest.mark.skipif(
    django.VERSION < (1, 10), reason="new-style middleware was added in Django 1.10"
)

skip_unless_old_style_middleware = pytest.mark.skipif(
    django.VERSION >= (2, 0), reason="old-style middleware was removed in Django 2.0"
)


@contextmanager
def app_with_scout(config=None):
    """
    Context manager that configures and installs the Scout plugin for Django.
    """
    # Enable Scout by default in tests.
    if config is None:
        config = {"SCOUT_MONITOR": True}

    # Disable running the agent.
    config["SCOUT_CORE_AGENT_LAUNCH"] = False

    # Setup according to https://docs.scoutapm.com/#django
    with override_settings(**config):
        # Prevent durable changes to MIDDLEWARE and MIDDLEWARE_CLASSES by
        # replacing them with a copy of their value.
        for name in ["MIDDLEWARE", "MIDDLEWARE_CLASSES"]:
            try:
                value = getattr(settings, name)
            except AttributeError:
                pass
            else:
                setattr(settings, name, value)
        # Scout settings must be overridden before inserting scout_apm.django
        # in INSTALLED_APPS because ScoutApmDjangoConfig.ready() accesses it.
        with modify_settings(INSTALLED_APPS={"prepend": "scout_apm.django"}):
            try:
                # Django initializes middleware when in creates the WSGI app.
                # Modifying MIDDLEWARE setting has no effect on the app.
                # Create a new WSGI app to account for the new middleware
                # that "scout_apm.django" injected.
                yield get_wsgi_application()
            finally:
                # Reset Scout configuration.
                Config.reset_all()


@pytest.fixture(autouse=True)
def finish_tracked_request_if_old_style_middlware():
    # It appears that the current implementation of old-style middleware
    # doesn't always pair start_span() and stop_span() calls. This leaks
    # unfinished TrackedRequest instances across tests.
    # Sweep the dirt under the rug until there's a better solution :-(
    try:
        yield
    finally:
        if django.VERSION < (2, 0):
            TrackedRequest.instance().finish()


def test_home(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/")
        assert response.status_int == 200

    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.django_app.home",
        "Middleware",
    ]


# During the transition between old-style and new-style middleware, Django
# defaults to the old style. Also test with the new style in that case.
@skip_unless_new_style_middleware
@skip_unless_old_style_middleware
def test_home_new_style(tracked_requests):
    with override_settings(MIDDLEWARE=[]):
        test_home(tracked_requests)


def test_hello(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200

    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.django_app.hello",
        "Middleware",
    ]


# During the transition between old-style and new-style middleware, Django
# defaults to the old style. Also test with the new style in that case.
@skip_unless_new_style_middleware
@skip_unless_old_style_middleware
def test_hello_new_style(tracked_requests):
    with override_settings(MIDDLEWARE=[]):
        test_hello(tracked_requests)


def test_not_found(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/not-found/", expect_errors=True)
        assert response.status_int == 404

    if django.VERSION < (1, 10) or settings.MIDDLEWARE is None:
        # Old style middleware doesn't currently pick up 404's
        assert len(tracked_requests) == 0
    else:
        assert len(tracked_requests) == 1
        spans = tracked_requests[0].complete_spans
        assert [s.operation for s in spans] == [
            "Template/Compile/<Unknown Template>",
            "Template/Render/<Unknown Template>",
            "Unknown",
            "Middleware",
        ]


# During the transition between old-style and new-style middleware, Django
# defaults to the old style. Also test with the new style in that case.
@skip_unless_new_style_middleware
@skip_unless_old_style_middleware
def test_not_found_new_style(tracked_requests):
    with override_settings(MIDDLEWARE=[]):
        test_not_found(tracked_requests)


def test_server_error(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/crash/", expect_errors=True)
        assert response.status_int == 500

    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    # Different processing order on old-style middleware
    if django.VERSION < (1, 10) or settings.MIDDLEWARE is None:
        expected = [
            "Controller/tests.integration.django_app.crash",
            "Template/Compile/<Unknown Template>",
            "Template/Render/<Unknown Template>",
            "Middleware",
        ]
    else:
        expected = [
            "Template/Compile/<Unknown Template>",
            "Template/Render/<Unknown Template>",
            "Controller/tests.integration.django_app.crash",
            "Middleware",
        ]
    assert [s.operation for s in spans] == expected


# During the transition between old-style and new-style middleware, Django
# defaults to the old style. Also test with the new style in that case.
@skip_unless_new_style_middleware
@skip_unless_old_style_middleware
def test_server_error_new_style(tracked_requests):
    with override_settings(MIDDLEWARE=[]):
        test_server_error(tracked_requests)


def test_sql(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/sql/")
        assert response.status_int == 200

    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "SQL/Query",
        "SQL/Many",
        "SQL/Query",
        "Controller/tests.integration.django_app.sql",
        "Middleware",
    ]


# Monkey patch should_capture_backtrace in order to keep the test fast.
@patch(
    "scout_apm.core.n_plus_one_call_set.NPlusOneCallSetItem.should_capture_backtrace"
)
def test_sql_capture_backtrace(should_capture_backtrace, tracked_requests):
    should_capture_backtrace.return_value = True
    with app_with_scout() as app:
        response = TestApp(app).get("/sql/")
        assert response.status_int == 200

    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "SQL/Query",
        "SQL/Many",
        "SQL/Query",
        "Controller/tests.integration.django_app.sql",
        "Middleware",
    ]


def test_template(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/template/")
        assert response.status_int == 200

    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    print([s.operation for s in spans])
    assert [s.operation for s in spans] == [
        "Template/Compile/<Unknown Template>",
        "Block/Render/name",
        "Template/Render/<Unknown Template>",
        "Controller/tests.integration.django_app.template",
        "Middleware",
    ]


@pytest.mark.xfail(reason="Test setup doesn't reset state fully at the moment.")
def test_no_monitor(tracked_requests):
    # With an empty config, "scout.monitor" defaults to "false".
    with app_with_scout({}) as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200

    assert len(tracked_requests) == 0


def fake_authentication_middleware(get_response):
    def middleware(request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = Mock()
        request.user.get_username.return_value = "scout"
        return get_response(request)

    return middleware


@skip_unless_new_style_middleware
def test_username(tracked_requests):
    with override_settings(MIDDLEWARE=[__name__ + ".fake_authentication_middleware"]):
        with app_with_scout() as app:
            response = TestApp(app).get("/hello/")
            assert response.status_int == 200

    assert len(tracked_requests) == 1
    tr = tracked_requests[0]
    assert tr.tags["username"] == "scout"


def crashy_authentication_middleware(get_response):
    def middleware(request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = Mock()
        request.user.get_username.side_effect = ValueError
        return get_response(request)

    return middleware


@skip_unless_new_style_middleware
def test_username_exception(tracked_requests):
    with override_settings(MIDDLEWARE=[__name__ + ".crashy_authentication_middleware"]):
        with app_with_scout() as app:
            response = TestApp(app).get("/hello/")
            assert response.status_int == 200

    assert len(tracked_requests) == 1
    tr = tracked_requests[0]
    assert "username" not in tr.tags


class FakeAuthenticationMiddleware(object):
    def process_request(self, request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = Mock()
        request.user.get_username.return_value = "scout"


@skip_unless_old_style_middleware
def test_old_style_username(tracked_requests):
    with override_settings(
        MIDDLEWARE_CLASSES=[__name__ + ".FakeAuthenticationMiddleware"]
    ):
        with app_with_scout() as app:
            response = TestApp(app).get("/hello/")
            assert response.status_int == 200

    assert len(tracked_requests) == 1
    tr = tracked_requests[0]
    print(tr.tags)
    assert tr.tags["username"] == "scout"


class CrashyAuthenticationMiddleware(object):
    def process_request(self, request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = Mock()
        request.user.get_username.side_effect = ValueError


@skip_unless_old_style_middleware
def test_old_style_username_exception(tracked_requests):
    with override_settings(
        MIDDLEWARE_CLASSES=[__name__ + ".CrashyAuthenticationMiddleware"]
    ):
        with app_with_scout() as app:
            response = TestApp(app).get("/hello/")
            assert response.status_int == 200

    assert len(tracked_requests) == 1
    tr = tracked_requests[0]
    assert "username" not in tr.tags


@pytest.mark.parametrize("list_or_tuple", [list, tuple])
@skip_unless_new_style_middleware
def test_middleware(list_or_tuple):
    with override_settings(
        MIDDLEWARE=list_or_tuple(["django.middleware.common.CommonMiddleware"])
    ):
        with app_with_scout():
            assert settings.MIDDLEWARE == list_or_tuple(
                [
                    "scout_apm.django.middleware.MiddlewareTimingMiddleware",
                    "django.middleware.common.CommonMiddleware",
                    "scout_apm.django.middleware.ViewTimingMiddleware",
                ]
            )


@pytest.mark.parametrize("list_or_tuple", [list, tuple])
@skip_unless_old_style_middleware
def test_old_style_middleware(list_or_tuple):
    with override_settings(
        MIDDLEWARE_CLASSES=list_or_tuple(["django.middleware.common.CommonMiddleware"])
    ):
        with app_with_scout():
            assert settings.MIDDLEWARE_CLASSES == list_or_tuple(
                [
                    "scout_apm.django.middleware.OldStyleMiddlewareTimingMiddleware",
                    "django.middleware.common.CommonMiddleware",
                    "scout_apm.django.middleware.OldStyleViewMiddleware",
                ]
            )


def test_application_root():
    """
    A BASE_DIR setting is mapped to the application_root config parameter.

    Django doesn't have a BASE_DIR setting. However the default project
    template creates it in order to define other settings. As a consequence,
    most Django projets have it.

    """
    base_dir = os.path.dirname(__file__)
    with override_settings(BASE_DIR=base_dir):
        with app_with_scout():
            assert Config().value("application_root") == base_dir
