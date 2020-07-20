# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import sys
from contextlib import contextmanager

import django
import pytest
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.http import HttpResponse
from django.test.utils import override_settings
from webtest import TestApp

from scout_apm.compat import datetime_to_timestamp, kwargs_only
from scout_apm.core.config import scout_config
from scout_apm.django.instruments.huey import ensure_huey_instrumented
from scout_apm.django.instruments.sql import ensure_sql_instrumented
from scout_apm.django.instruments.template import ensure_templates_instrumented
from tests.compat import mock
from tests.integration import django_app
from tests.integration.util import (
    parametrize_filtered_params,
    parametrize_queue_time_header_name,
    parametrize_user_ip_headers,
)
from tests.tools import (
    delete_attributes,
    n_plus_one_thresholds,
    pretend_package_unavailable,
    skip_if_python_2,
)

try:
    from django.urls import resolve
except ImportError:
    from django.core.urlresolvers import resolve


if sys.version_info >= (3,):
    from pathlib import Path
else:
    Path = None


skip_unless_new_style_middleware = pytest.mark.skipif(
    django.VERSION < (1, 10), reason="new-style middleware was added in Django 1.10"
)

skip_unless_old_style_middleware = pytest.mark.skipif(
    django.VERSION >= (1, 10), reason="new-style middleware was added in Django 1.10"
)


@pytest.fixture(autouse=True)
def ensure_no_django_config_applied_after_tests():
    """
    Prevent state leaking into the non-Django tests. All config needs to be set
    with @override_settings so that the on_setting_changed handler removes
    them from the dictionary afterwards.
    """
    yield
    assert all(
        (key != "BASE_DIR" and not key.startswith("SCOUT_")) for key in dir(settings)
    )


@contextmanager
@kwargs_only
def app_with_scout(**settings):
    """
    Context manager that simply overrides settings. Unlike the other web
    frameworks, Django is a singleton application, so we can't smoothly
    uninstall and reinstall scout per test.
    """
    settings.setdefault("SCOUT_MONITOR", True)
    settings["SCOUT_CORE_AGENT_LAUNCH"] = False
    with override_settings(**settings):
        # Have to create a new WSGI app each time because the middleware stack
        # within it is static
        app = get_wsgi_application()
        # Run Django checks on first use
        if not getattr(app_with_scout, "startup_ran", False):
            call_command("migrate")
            call_command("check")
            app_with_scout.startup_ran = True
        yield app


def make_admin_user():
    from django.contrib.auth.models import User

    password = "password"
    user = User.objects.create_superuser(
        id=1, username="admin", email="admin@example.com", password=password
    )
    user.testing_password = password
    return user


@pytest.mark.parametrize(
    "func",
    [ensure_huey_instrumented, ensure_sql_instrumented, ensure_templates_instrumented],
)
def test_instruments_idempotent(func):
    """
    Check second call doesn't crash (should be a no-op)
    """
    func()


def test_on_setting_changed_application_root():
    with app_with_scout(BASE_DIR="/tmp/foobar"):
        assert scout_config.value("application_root") == "/tmp/foobar"
    assert scout_config.value("application_root") == ""


@skip_if_python_2
def test_on_setting_changed_application_root_pathlib():
    with app_with_scout(BASE_DIR=Path("/tmp/foobar")):
        value = scout_config.value("application_root")
        assert isinstance(value, str)
        assert value == "/tmp/foobar"
    assert scout_config.value("application_root") == ""


def test_on_setting_changed_monitor():
    with app_with_scout(SCOUT_MONITOR=True):
        assert scout_config.value("monitor") is True
    assert scout_config.value("monitor") is False


def test_home(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.tags["user_ip"] is None
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.django_app.home",
        "Middleware",
    ]


def test_home_ignored(tracked_requests):
    with app_with_scout(SCOUT_IGNORE="/") as app:
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
    with app_with_scout(SCOUT_COLLECT_REMOTE_IP=False) as app:
        TestApp(app).get(
            "/", extra_environ={str("REMOTE_ADDR"): "1.1.1.1"},
        )

    tracked_request = tracked_requests[0]
    assert "user_ip" not in tracked_request.tags


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


def test_not_found(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/not-found/", expect_errors=True)

    assert response.status_int == 404
    assert len(tracked_requests) == 0


def test_server_error(tracked_requests):
    with app_with_scout(DEBUG_PROPAGATE_EXCEPTIONS=False) as app:
        response = TestApp(app).get("/crash/", expect_errors=True)

    assert response.status_int == 500
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["error"] == "true"
    spans = tracked_requests[0].complete_spans
    operations = [s.operation for s in spans]
    if django.VERSION >= (1, 9):
        # Changed in Django 1.9 or later (we only test 1.8 and 1.11 at time of
        # writing)
        expected_operations = [
            "Template/Compile/<Unknown Template>",
            "Template/Render/<Unknown Template>",
            "Controller/tests.integration.django_app.crash",
            "Middleware",
        ]
    else:
        expected_operations = [
            "Controller/tests.integration.django_app.crash",
            "Middleware",
        ]
    assert operations == expected_operations


def test_return_error(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/return-error/", expect_errors=True)

    assert response.status_int == 503
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["error"] == "true"
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.django_app.return_error",
        "Middleware",
    ]


def test_cbv(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/cbv/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.django_app.CbvView",
        "Middleware",
    ]


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
    assert spans[0].tags["db.statement"] == "CREATE TABLE IF NOT EXISTS test(item)"
    assert spans[1].tags["db.statement"] == "INSERT INTO test(item) VALUES(%s)"
    assert spans[2].tags["db.statement"] == "SELECT item from test"


def test_sql_kwargs(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/sql-kwargs/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "SQL/Query",
        "SQL/Many",
        "Controller/tests.integration.django_app.sql_kwargs",
        "Middleware",
    ]
    assert spans[0].tags["db.statement"] == "CREATE TABLE IF NOT EXISTS test(item)"
    assert spans[1].tags["db.statement"] == "INSERT INTO test(item) VALUES(%s)"


def test_sql_execute_type_error(tracked_requests):
    """
    Check that broken usage of the monkey-patched cursor methods doesn't cause
    any irregular crash
    """
    with app_with_scout() as app:
        response = TestApp(app).get("/sql-type-errors/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    # Nothing tracked, but it worked fine
    assert [s.operation for s in spans] == [
        "Controller/tests.integration.django_app.sql_type_errors",
        "Middleware",
    ]


def test_sql_capture_backtrace(tracked_requests):
    with n_plus_one_thresholds(count=1, duration=0.0), app_with_scout() as app:
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
    assert "stack" in spans[0].tags
    assert "stack" in spans[1].tags
    assert "stack" in spans[2].tags


def test_sql_capture_backtrace_many(tracked_requests):
    # Set count threshold at 2 so only executemany statement is captured
    with n_plus_one_thresholds(count=2, duration=0.0), app_with_scout() as app:
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
    assert "stack" not in spans[0].tags
    assert "stack" in spans[1].tags
    assert "stack" not in spans[2].tags


def test_template(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/template/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Template/Compile/<Unknown Template>",
        "Block/Render/name",
        "Template/Render/<Unknown Template>",
        "Controller/tests.integration.django_app.template",
        "Middleware",
    ]


def test_template_response(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/template-response/")

    assert response.status_int == 200
    assert response.text == "Hello World!!!"
    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "Template/Compile/<Unknown Template>",
        "Block/Render/name",
        "Template/Render/<Unknown Template>",
        "Controller/tests.integration.django_app.template_response",
        "Middleware",
    ]


@pytest.mark.skipif(
    django.VERSION < (1, 9),
    reason="Django 1.9 added the model_admin attribute this functionality depends on",
)
@pytest.mark.parametrize(
    "url, expected_op_name",
    [
        [
            "/admin/auth/user/",
            "Controller/django.contrib.auth.admin.UserAdmin.changelist_view",
        ],
        [
            "/admin/auth/user/1/change/",
            "Controller/django.contrib.auth.admin.UserAdmin.change_view",
        ],
    ],
)
def test_admin_view_operation_name(url, expected_op_name, tracked_requests):
    with app_with_scout() as app:
        admin_user = make_admin_user()
        test_app = TestApp(app)
        login_response = test_app.get("/admin/login/")
        assert login_response.status_int == 200
        form = login_response.form
        form["username"] = admin_user.username
        form["password"] = admin_user.testing_password
        form.submit()
        response = test_app.get(url)

    assert response.status_int == 200
    # 3 requests for login GET and POST, then admin page
    assert len(tracked_requests) == 3
    # We only care about the last
    tracked_request = tracked_requests[-1]
    span = tracked_request.complete_spans[-2]
    assert span.operation == expected_op_name


@pytest.mark.parametrize(
    "url, expected_op_name",
    [
        [
            "/drf-router/users/",
            "Controller/tests.integration.django_app.UserViewSet.list",
        ],
        [
            "/drf-router/users/1/",
            "Controller/tests.integration.django_app.UserViewSet.retrieve",
        ],
    ],
)
def test_django_rest_framework_api_operation_name(
    url, expected_op_name, tracked_requests
):
    with app_with_scout() as app:
        make_admin_user()
        response = TestApp(app).get(url)

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    spans = tracked_requests[0].complete_spans
    assert [s.operation for s in spans] == [
        "SQL/Query",
        expected_op_name,
        "Middleware",
    ]


def skip_if_no_tastypie():
    # This would make more sense as a test decorator, but can't be one because
    # it requires the Django application to be constructed first, under
    # app_with_scout()
    if not django_app.tastypie_api:
        pytest.skip("No Tastypie")


@pytest.mark.parametrize(
    "url, expected_op_name",
    [
        [
            "/tastypie-api/v1/user/1/",
            "Controller/tests.integration.django_app.UserResource.get_detail",
        ],
        [
            "/tastypie-api/v1/user/",
            "Controller/tests.integration.django_app.UserResource.get_list",
        ],
    ],
)
def test_tastypie_api_operation_name(url, expected_op_name, tracked_requests):
    with app_with_scout() as app:
        skip_if_no_tastypie()
        make_admin_user()
        response = TestApp(app).get(url, {"format": "json"})

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    span = tracked_request.complete_spans[-2]
    assert span.operation == expected_op_name


def test_tastypie_api_operation_name_fail_no_tastypie(tracked_requests):
    with app_with_scout() as app:
        skip_if_no_tastypie()
        with pretend_package_unavailable("tastypie"):
            response = TestApp(app).get("/tastypie-api/v1/user/", {"format": "json"})

    assert response.status_int == 200
    span = tracked_requests[0].complete_spans[-2]
    assert span.operation == "Controller/tastypie.resources.wrapper"


@skip_if_python_2
def test_tastypie_api_operation_name_fail_no_wrapper(tracked_requests):
    with app_with_scout() as app:
        skip_if_no_tastypie()
        url = "/tastypie-api/v1/user/"
        view_func = resolve(url).func
        with delete_attributes(view_func, "__wrapped__"):
            response = TestApp(app).get(url, {"format": "json"})

    assert response.status_int == 200
    span = tracked_requests[0].complete_spans[-2]
    assert span.operation == "Controller/tastypie.resources.wrapper"


@skip_if_python_2
def test_tastypie_api_operation_name_fail_no_closure(tracked_requests):
    with app_with_scout() as app:
        skip_if_no_tastypie()
        url = "/tastypie-api/v1/user/"
        view_func = resolve(url).func
        with mock.patch.object(view_func, "__wrapped__"):
            response = TestApp(app).get(url, {"format": "json"})

    assert response.status_int == 200
    span = tracked_requests[0].complete_spans[-2]
    assert span.operation == "Controller/tastypie.resources.wrapper"


def test_no_monitor(tracked_requests):
    with app_with_scout(SCOUT_MONITOR=False) as app:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert tracked_requests == []


def test_no_monitor_server_error(tracked_requests):
    with app_with_scout(SCOUT_MONITOR=False, DEBUG_PROPAGATE_EXCEPTIONS=False) as app:
        response = TestApp(app).get("/crash/", expect_errors=True)

    assert response.status_int == 500
    assert tracked_requests == []


def fake_authentication_middleware(get_response):
    def middleware(request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = mock.Mock()
        request.user.get_username.return_value = "scout"
        return get_response(request)

    return middleware


@skip_unless_new_style_middleware
def test_username(tracked_requests):
    new_middleware = (
        settings.MIDDLEWARE[:-1]
        + [__name__ + ".fake_authentication_middleware"]
        + settings.MIDDLEWARE[-1:]
    )
    with app_with_scout(MIDDLEWARE=new_middleware) as app:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["username"] == "scout"


def crashy_authentication_middleware(get_response):
    def middleware(request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = mock.Mock()
        request.user.get_username.side_effect = ValueError
        return get_response(request)

    return middleware


@skip_unless_new_style_middleware
def test_username_exception(tracked_requests):
    new_middleware = (
        settings.MIDDLEWARE[:-1]
        + [__name__ + ".crashy_authentication_middleware"]
        + settings.MIDDLEWARE[-1:]
    )
    with app_with_scout(MIDDLEWARE=new_middleware) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert "username" not in tracked_request.tags


class FakeAuthenticationMiddleware(object):
    def process_request(self, request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = mock.Mock()
        request.user.get_username.return_value = "scout"


@skip_unless_old_style_middleware
def test_old_style_username(tracked_requests):
    new_middleware = (
        settings.MIDDLEWARE_CLASSES[:-1]
        + [__name__ + ".FakeAuthenticationMiddleware"]
        + settings.MIDDLEWARE_CLASSES[-1:]
    )
    with app_with_scout(MIDDLEWARE_CLASSES=new_middleware) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["username"] == "scout"


class CrashyAuthenticationMiddleware(object):
    def process_request(self, request):
        # Mock the User instance to avoid a dependency on django.contrib.auth.
        request.user = mock.Mock()
        request.user.get_username.side_effect = ValueError


@skip_unless_old_style_middleware
def test_old_style_username_exception(tracked_requests):
    new_middleware = (
        settings.MIDDLEWARE_CLASSES[:-1]
        + [__name__ + ".CrashyAuthenticationMiddleware"]
        + settings.MIDDLEWARE_CLASSES[-1:]
    )
    with app_with_scout(MIDDLEWARE_CLASSES=new_middleware) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert "username" not in tracked_request.tags


def urlconf_middleware(get_response):
    def middleware(request):
        sys.modules["tests.integration.django_app_second_copy"] = django_app
        request.urlconf = "tests.integration.django_app_second_copy"
        return get_response(request)

    return middleware


@skip_unless_new_style_middleware
def test_urlconf(tracked_requests):
    new_middleware = (
        settings.MIDDLEWARE[:-1]
        + [__name__ + ".urlconf_middleware"]
        + settings.MIDDLEWARE[-1:]
    )
    with app_with_scout(MIDDLEWARE=new_middleware) as app:
        response = TestApp(app).get("/hello/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["urlconf"] == "tests.integration.django_app_second_copy"


class UrlconfMiddleware(object):
    def process_request(self, request):
        sys.modules["tests.integration.django_app_second_copy"] = django_app
        request.urlconf = "tests.integration.django_app_second_copy"


@skip_unless_old_style_middleware
def test_old_style_urlconf(tracked_requests):
    new_middleware = (
        settings.MIDDLEWARE_CLASSES[:-1]
        + [__name__ + ".UrlconfMiddleware"]
        + settings.MIDDLEWARE_CLASSES[-1:]
    )
    with app_with_scout(MIDDLEWARE_CLASSES=new_middleware) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["urlconf"] == "tests.integration.django_app_second_copy"


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


@skip_unless_old_style_middleware
@pytest.mark.parametrize("list_or_tuple", [list, tuple])
@pytest.mark.parametrize("preinstalled", [True, False])
def test_install_middleware_old_style(list_or_tuple, preinstalled):
    if preinstalled:
        middleware = list_or_tuple(
            [
                "scout_apm.django.middleware.OldStyleMiddlewareTimingMiddleware",
                "django.middleware.common.CommonMiddleware",
                "scout_apm.django.middleware.OldStyleViewMiddleware",
            ]
        )
    else:
        middleware = list_or_tuple(["django.middleware.common.CommonMiddleware"])

    with override_settings(MIDDLEWARE_CLASSES=middleware):
        apps.get_app_config("scout_apm").install_middleware()

        assert settings.MIDDLEWARE_CLASSES == list_or_tuple(
            [
                "scout_apm.django.middleware.OldStyleMiddlewareTimingMiddleware",
                "django.middleware.common.CommonMiddleware",
                "scout_apm.django.middleware.OldStyleViewMiddleware",
            ]
        )


@skip_unless_new_style_middleware
@pytest.mark.parametrize("list_or_tuple", [list, tuple])
@pytest.mark.parametrize("preinstalled", [True, False])
def test_install_middleware_new_style(list_or_tuple, preinstalled):
    if preinstalled:
        middleware = list_or_tuple(
            [
                "scout_apm.django.middleware.MiddlewareTimingMiddleware",
                "django.middleware.common.CommonMiddleware",
                "scout_apm.django.middleware.ViewTimingMiddleware",
            ]
        )
    else:
        middleware = list_or_tuple(["django.middleware.common.CommonMiddleware"])

    with override_settings(MIDDLEWARE=middleware):
        apps.get_app_config("scout_apm").install_middleware()

        assert settings.MIDDLEWARE == list_or_tuple(
            [
                "scout_apm.django.middleware.MiddlewareTimingMiddleware",
                "django.middleware.common.CommonMiddleware",
                "scout_apm.django.middleware.ViewTimingMiddleware",
            ]
        )


class OldStyleOnRequestResponseMiddleware:
    def process_request(self, request):
        return HttpResponse("on_request response!")


@skip_unless_old_style_middleware
@pytest.mark.parametrize("middleware_index", [0, 1, 999])
def test_old_style_on_request_response_middleware(middleware_index, tracked_requests):
    """
    Test the case that a middleware got added/injected that generates a
    response in its process_request, triggering Django's middleware shortcut
    path. This will not be counted as a real request because it doesn't reach a
    view.
    """
    new_middleware = (
        settings.MIDDLEWARE_CLASSES[:middleware_index]
        + [__name__ + "." + OldStyleOnRequestResponseMiddleware.__name__]
        + settings.MIDDLEWARE_CLASSES[middleware_index:]
    )
    with app_with_scout(MIDDLEWARE_CLASSES=new_middleware) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "on_request response!"
    assert len(tracked_requests) == 0


class OldStyleOnResponseResponseMiddleware:
    def process_response(self, request, response):
        return HttpResponse("process_response response!")


@skip_unless_old_style_middleware
@pytest.mark.parametrize("middleware_index", [0, 1, 999])
def test_old_style_on_response_response_middleware(middleware_index, tracked_requests):
    """
    Test the case that a middleware got added/injected that generates a fresh
    response in its process_response. This will count as a real request because
    it reaches the view, but then the view's response gets replaced on the way
    out.
    """
    new_middleware = (
        settings.MIDDLEWARE_CLASSES[:middleware_index]
        + [__name__ + "." + OldStyleOnResponseResponseMiddleware.__name__]
        + settings.MIDDLEWARE_CLASSES[middleware_index:]
    )
    with app_with_scout(MIDDLEWARE_CLASSES=new_middleware) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "process_response response!"
    assert len(tracked_requests) == 1


class OldStyleOnViewResponseMiddleware:
    def process_view(self, request, view_func, view_func_args, view_func_kwargs):
        return HttpResponse("process_view response!")


@skip_unless_old_style_middleware
@pytest.mark.parametrize("middleware_index", [0, 1, 999])
def test_old_style_on_view_response_middleware(middleware_index, tracked_requests):
    """
    Test the case that a middleware got added/injected that generates a fresh
    response in its process_response. This will count as a real request because
    it reaches the view, but then the view's response gets replaced on the way
    out.
    """
    new_middleware = (
        settings.MIDDLEWARE_CLASSES[:middleware_index]
        + [__name__ + "." + OldStyleOnViewResponseMiddleware.__name__]
        + settings.MIDDLEWARE_CLASSES[middleware_index:]
    )
    with app_with_scout(MIDDLEWARE_CLASSES=new_middleware) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "process_view response!"
    # If the middleware is before OldStyleViewMiddleware, its process_view
    # won't be called and we won't know to mark the request as real, so it
    # won't be tracked.
    if middleware_index != 999:
        assert len(tracked_requests) == 0
    else:
        assert len(tracked_requests) == 1


class OldStyleOnExceptionResponseMiddleware:
    def process_exception(self, request, exception):
        return HttpResponse("process_exception response!")


@skip_unless_old_style_middleware
@pytest.mark.parametrize("middleware_index", [0, 1, 999])
def test_old_style_on_exception_response_middleware(middleware_index, tracked_requests):
    """
    Test the case that a middleware got added/injected that generates a
    response in its process_exception. This should follow basically the same
    path as normal view exception, since Django applies process_response from
    middleware on the outgoing response.
    """
    new_middleware = (
        settings.MIDDLEWARE_CLASSES[:middleware_index]
        + [__name__ + "." + OldStyleOnExceptionResponseMiddleware.__name__]
        + settings.MIDDLEWARE_CLASSES[middleware_index:]
    )
    with app_with_scout(MIDDLEWARE_CLASSES=new_middleware) as app:
        response = TestApp(app).get("/crash/")

    assert response.status_int == 200
    assert response.text == "process_exception response!"
    assert len(tracked_requests) == 1

    # In the case that the middleware is added after OldStyleViewMiddleware,
    # its process_exception won't be called so we won't know it's an error.
    # Nothing we can do there - but it's a rare case, since we programatically
    # add our middleware at the end of the stack.
    if middleware_index != 999:
        assert tracked_requests[0].tags["error"] == "true"


class OldStyleExceptionOnRequestMiddleware:
    def process_request(self, request):
        raise ValueError("Woops!")


@skip_unless_old_style_middleware
@pytest.mark.parametrize("middleware_index", [0, 1, 999])
def test_old_style_exception_on_request_middleware(middleware_index, tracked_requests):
    """
    Test the case that a middleware got added/injected that raises an exception
    in its process_request.
    """
    new_middleware = (
        settings.MIDDLEWARE_CLASSES[:middleware_index]
        + [__name__ + "." + OldStyleExceptionOnRequestMiddleware.__name__]
        + settings.MIDDLEWARE_CLASSES[middleware_index:]
    )
    with app_with_scout(
        MIDDLEWARE_CLASSES=new_middleware, DEBUG_PROPAGATE_EXCEPTIONS=False
    ) as app:
        response = TestApp(app).get("/", expect_errors=True)

    assert response.status_int == 500
    assert len(tracked_requests) == 0


@skip_unless_old_style_middleware
@pytest.mark.parametrize("url,expected_status", [("/", 200), ("/crash/", 500)])
def test_old_style_timing_middleware_deleted(url, expected_status, tracked_requests):
    """
    Test the case that some adversarial thing fiddled with the settings
    after app.ready() (like we do!) in order to remove the
    OldStyleMiddlewareTimingMiddleware. The tracked request won't be started
    but OldStyleViewMiddleware defends against this.
    """
    new_middleware = settings.MIDDLEWARE_CLASSES[1:]
    with app_with_scout(
        MIDDLEWARE_CLASSES=new_middleware, DEBUG_PROPAGATE_EXCEPTIONS=False
    ) as app:
        response = TestApp(app).get(url, expect_errors=True)

    assert response.status_int == expected_status
    assert len(tracked_requests) == 0


@skip_unless_old_style_middleware
def test_old_style_view_middleware_deleted(tracked_requests):
    """
    Test the case that some adversarial thing fiddled with the settings
    after app.ready() (like we do!) in order to remove the
    OldStyleViewMiddleware. The tracked request won't be marked as real since
    its process_view won't have run.
    """
    new_middleware = settings.MIDDLEWARE_CLASSES[:1]
    with app_with_scout(MIDDLEWARE_CLASSES=new_middleware) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert len(tracked_requests) == 0


def test_huey_basic_task(tracked_requests):
    with app_with_scout():
        from huey.contrib.djhuey import task

        @task()
        def hello():
            return "Hello World!"

        result = hello()
        value = result(blocking=True, timeout=1)

    assert value == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert "task_id" in tracked_request.tags
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_django.hello"
