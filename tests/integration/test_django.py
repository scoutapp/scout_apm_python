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


new_style = pytest.mark.skipif(
    django.VERSION < (1, 10), reason="new-style middleware was added in Django 1.10"
)

old_style = pytest.mark.skipif(
    django.VERSION >= (2, 0), reason="old-style middleware was removed in Django 2.0"
)


@contextmanager
def app_with_scout(config=None):
    """
    Context manager that configures and installs the Scout plugin for Bottle.

    """
    # Enable Scout by default in tests.
    if config is None:
        config = {"SCOUT_MONITOR": True}

    # Disable running the agent.
    config["SCOUT_CORE_AGENT_LAUNCH"] = False

    # Setup according to http://help.apm.scoutapp.com/#django
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


@pytest.fixture
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


def test_home(finish_tracked_request_if_old_style_middlware):
    with app_with_scout() as app:
        response = TestApp(app).get("/")
        assert response.status_int == 200


# During the transition between old-style and new-style middleware, Django
# defaults to the old style. Also test with the new style in that case.
@new_style
@old_style
def test_home_new_style(finish_tracked_request_if_old_style_middlware):
    with override_settings(MIDDLEWARE=[]):
        test_home(finish_tracked_request_if_old_style_middlware)


def test_hello(finish_tracked_request_if_old_style_middlware):
    with app_with_scout() as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200


# During the transition between old-style and new-style middleware, Django
# defaults to the old style. Also test with the new style in that case.
@new_style
@old_style
def test_hello_new_style(finish_tracked_request_if_old_style_middlware):
    with override_settings(MIDDLEWARE=[]):
        test_hello(finish_tracked_request_if_old_style_middlware)


def test_not_found(finish_tracked_request_if_old_style_middlware):
    with app_with_scout() as app:
        response = TestApp(app).get("/not-found/", expect_errors=True)
        assert response.status_int == 404


# During the transition between old-style and new-style middleware, Django
# defaults to the old style. Also test with the new style in that case.
@new_style
@old_style
def test_not_found_new_style(finish_tracked_request_if_old_style_middlware):
    with override_settings(MIDDLEWARE=[]):
        test_not_found(finish_tracked_request_if_old_style_middlware)


def test_server_error(finish_tracked_request_if_old_style_middlware):
    with app_with_scout() as app:
        response = TestApp(app).get("/crash/", expect_errors=True)
        assert response.status_int == 500


# During the transition between old-style and new-style middleware, Django
# defaults to the old style. Also test with the new style in that case.
@new_style
@old_style
def test_server_error_new_style(finish_tracked_request_if_old_style_middlware):
    with override_settings(MIDDLEWARE=[]):
        test_server_error(finish_tracked_request_if_old_style_middlware)


def test_sql(finish_tracked_request_if_old_style_middlware):
    with app_with_scout() as app:
        response = TestApp(app).get("/sql/")
        assert response.status_int == 200


# Monkey patch should_capture_backtrace in order to keep the test fast.
@patch(
    "scout_apm.core.n_plus_one_call_set.NPlusOneCallSetItem.should_capture_backtrace"
)
def test_sql_capture_backtrace(
    should_capture_backtrace, finish_tracked_request_if_old_style_middlware
):
    should_capture_backtrace.return_value = True
    with app_with_scout() as app:
        response = TestApp(app).get("/sql/")
        assert response.status_int == 200


def test_template(finish_tracked_request_if_old_style_middlware):
    with app_with_scout() as app:
        response = TestApp(app).get("/template/")
        assert response.status_int == 200


def test_no_monitor(finish_tracked_request_if_old_style_middlware):
    # With an empty config, "scout.monitor" defaults to "false".
    with app_with_scout({}) as app:
        response = TestApp(app).get("/hello/")
        assert response.status_int == 200


def fake_authentication_middleware(get_response):
    def middleware(request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = Mock()
        request.user.get_username.return_value = "scout"
        return get_response(request)

    return middleware


@new_style
def test_username():
    with override_settings(MIDDLEWARE=[__name__ + ".fake_authentication_middleware"]):
        with app_with_scout() as app:
            response = TestApp(app).get("/hello/")
            assert response.status_int == 200


def crashy_authentication_middleware(get_response):
    def middleware(request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = Mock()
        request.user.get_username.side_effect = ValueError
        return get_response(request)

    return middleware


@new_style
def test_username_exception():
    with override_settings(MIDDLEWARE=[__name__ + ".crashy_authentication_middleware"]):
        with app_with_scout() as app:
            response = TestApp(app).get("/hello/")
            assert response.status_int == 200


class FakeAuthenticationMiddleware(object):
    def process_request(self, request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = Mock()
        request.user.get_username.return_value = "scout"


@old_style
def test_old_style_username(finish_tracked_request_if_old_style_middlware):
    with override_settings(
        MIDDLEWARE_CLASSES=[__name__ + ".FakeAuthenticationMiddleware"]
    ):
        with app_with_scout() as app:
            response = TestApp(app).get("/hello/")
            assert response.status_int == 200


class CrashyAuthenticationMiddleware(object):
    def process_request(self, request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = Mock()
        request.user.get_username.side_effect = ValueError


@old_style
def test_old_style_username_exception(finish_tracked_request_if_old_style_middlware):
    with override_settings(
        MIDDLEWARE_CLASSES=[__name__ + ".CrashyAuthenticationMiddleware"]
    ):
        with app_with_scout() as app:
            response = TestApp(app).get("/hello/")
            assert response.status_int == 200


@pytest.mark.parametrize("list_or_tuple", [list, tuple])
@new_style
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
@old_style
def test_old_style_middleware(
    list_or_tuple, finish_tracked_request_if_old_style_middlware
):
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
