# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from contextlib import contextmanager

import pytest

from scout_apm.api import Config
from scout_apm.compat import kwargs_only
from scout_apm.core.error import ErrorMonitor
from scout_apm.core.web_requests import RequestComponents


@contextmanager
@kwargs_only
def app_with_scout(scout_config=None):
    """
    Context manager that configures and installs the Scout plugin.
    """
    # Enable Scout by default in tests.
    if scout_config is None:
        scout_config = {}

    scout_config.setdefault("monitor", True)
    scout_config.setdefault("errors_enabled", True)
    Config.set(**scout_config)

    try:
        yield
    finally:
        # Reset Scout configuration.
        Config.reset_all()


def test_monitor_not_configured(error_monitor_errors):
    with app_with_scout(scout_config={"errors_enabled": False}):
        ErrorMonitor.send(None)
    assert len(error_monitor_errors) == 0


def test_monitor_ignore_exceptions(error_monitor_errors):
    with app_with_scout(
        scout_config={"errors_ignored_exceptions": [ZeroDivisionError]}
    ):
        try:
            1 / 0
        except ZeroDivisionError:
            exc_info = sys.exc_info()
        ErrorMonitor.send(exc_info, request_path="")
    assert len(error_monitor_errors) == 0


@pytest.mark.parametrize(
    "path, params, session, environment, request_components, "
    "custom_controller, custom_params, expected_error",
    [
        (
            "/test/",
            None,
            None,
            None,
            None,
            None,
            None,
            {
                "exception_class": "ZeroDivisionError",
                "message": "division by zero",
                "request_id": "sample_id",
                "request_uri": "/test/",
                "request_params": None,
                "request_session": None,
                "environment": None,
                "request_components": None,
                "context": {"spam": "foo"},
                "host": None,
                "revision_sha": "",
            },
        ),
        (
            "/test/",
            None,
            None,
            None,
            None,
            "test-controller",
            None,
            {
                "exception_class": "ZeroDivisionError",
                "message": "division by zero",
                "request_id": "sample_id",
                "request_uri": "/test/",
                "request_params": None,
                "request_session": None,
                "environment": None,
                "request_components": {
                    "module": None,
                    "controller": "test-controller",
                    "action": None,
                },
                "context": {"spam": "foo"},
                "host": None,
                "revision_sha": "",
            },
        ),
        (
            "/test/",
            [("foo", "bar")],
            {"spam": "eggs"},
            {"PASSWORD": "hunter2"},
            RequestComponents("sample.app", "DataView", "detail"),
            None,
            None,
            {
                "exception_class": "ZeroDivisionError",
                "message": "division by zero",
                "request_id": "sample_id",
                "request_uri": "/test/",
                "request_params": [("foo", "bar")],
                "request_session": {"spam": "eggs"},
                "environment": {"PASSWORD": "[FILTERED]"},
                "request_components": {
                    "module": "sample.app",
                    "controller": "DataView",
                    "action": "detail",
                },
                "context": {"spam": "foo"},
                "host": None,
                "revision_sha": "",
            },
        ),
        (
            "/test/",
            [("foo", "bar")],
            {"spam": "eggs"},
            {"PASSWORD": "hunter2"},
            RequestComponents("sample.app", "DataView", "detail"),
            "test-controller",
            {"baz": 3},
            {
                "exception_class": "ZeroDivisionError",
                "message": "division by zero",
                "request_id": "sample_id",
                "request_uri": "/test/",
                "request_params": [("foo", "bar")],
                "request_session": {"spam": "eggs"},
                "environment": {"PASSWORD": "[FILTERED]"},
                "request_components": {
                    "module": "sample.app",
                    "controller": "test-controller",
                    "action": "detail",
                },
                "context": {"spam": "foo", "custom_params": {"baz": 3}},
                "host": None,
                "revision_sha": "",
            },
        ),
    ],
)
def test_monitor(
    path,
    params,
    session,
    environment,
    request_components,
    custom_controller,
    custom_params,
    expected_error,
    tracked_request,
    error_monitor_errors,
):
    with app_with_scout():
        tracked_request.request_id = "sample_id"
        tracked_request.tags["spam"] = "foo"
        exc_info = 0
        try:
            1 / 0
        except ZeroDivisionError:
            exc_info = sys.exc_info()
        ErrorMonitor.send(
            exc_info,
            request_components=request_components,
            request_path=path,
            request_params=params,
            session=session,
            environment=environment,
            custom_controller=custom_controller,
            custom_params=custom_params,
        )

    assert len(error_monitor_errors) == 1
    error = error_monitor_errors[0]
    # Remove the trace from the error as it bloats the test.
    filepath, line, func_str = error.pop("trace")[0].split(":")
    assert filepath.endswith("tests/unit/core/test_error.py")
    # The line number changes between python versions. Make sure it's not empty.
    assert line
    assert func_str == "in test_monitor"
    assert error == expected_error
