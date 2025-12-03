# coding=utf-8

import logging
import os
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
    "custom_controller, scm_subdirectory, custom_params, expected_error",
    [
        (
            "/test/",
            None,
            None,
            None,
            None,
            None,
            "scm",
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
                "context": {"spam": "foo", "transaction_id": "sample_id"},
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
                "context": {"spam": "foo", "transaction_id": "sample_id"},
                "host": None,
                "revision_sha": "",
            },
        ),
        (
            "/test/",
            {"foo": ["bar"]},
            {"spam": "eggs"},
            {"PASSWORD": "hunter2"},
            RequestComponents("sample.app", "DataView", "detail"),
            None,
            "scm",
            None,
            {
                "exception_class": "ZeroDivisionError",
                "message": "division by zero",
                "request_id": "sample_id",
                "request_uri": "/test/",
                "request_params": {"foo": ["bar"]},
                "request_session": {"spam": "eggs"},
                "environment": {"PASSWORD": "[FILTERED]"},
                "request_components": {
                    "module": "sample.app",
                    "controller": "DataView",
                    "action": "detail",
                },
                "context": {"spam": "foo", "transaction_id": "sample_id"},
                "host": None,
                "revision_sha": "",
            },
        ),
        (
            "/test/",
            {"foo": ["bar"]},
            {"spam": "eggs"},
            {"PASSWORD": "hunter2"},
            RequestComponents("sample.app", "DataView", "detail"),
            "test-controller",
            "scm",
            {"baz": 3},
            {
                "exception_class": "ZeroDivisionError",
                "message": "division by zero",
                "request_id": "sample_id",
                "request_uri": "/test/",
                "request_params": {"foo": ["bar"]},
                "request_session": {"spam": "eggs"},
                "environment": {"PASSWORD": "[FILTERED]"},
                "request_components": {
                    "module": "sample.app",
                    "controller": "test-controller",
                    "action": "detail",
                },
                "context": {
                    "spam": "foo",
                    "transaction_id": "sample_id",
                    "custom_params": {"baz": 3},
                },
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
    scm_subdirectory,
    custom_params,
    expected_error,
    tracked_request,
    error_monitor_errors,
    caplog,
):
    with app_with_scout(scout_config={"scm_subdirectory": scm_subdirectory}):
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
    expected_filepath = "tests/unit/core/test_error.py"
    if scm_subdirectory:
        expected_filepath = os.path.join(scm_subdirectory, expected_filepath)
    assert filepath.endswith(expected_filepath)
    # The line number changes between python versions. Make sure it's not empty.
    assert line
    assert func_str == "in test_monitor"
    assert error == expected_error
    assert (
        "scout_apm.core.error",
        logging.DEBUG,
        "Sending error for request: sample_id.",
    ) in caplog.record_tuples


def test_monitor_with_logged_payload(
    tracked_request,
    error_monitor_errors,
    caplog,
):
    with app_with_scout(scout_config={"log_payload_content": True}):
        tracked_request.request_id = "sample_id"
        tracked_request.tags["spam"] = "foo"
        exc_info = 0
        try:
            1 / 0
        except ZeroDivisionError:
            exc_info = sys.exc_info()
        ErrorMonitor.send(
            exc_info,
            request_components=RequestComponents("sample.app", "DataView", "detail"),
            request_path="/test/",
        )

    assert len(error_monitor_errors) == 1

    # Find the logged message.
    actual_message = None
    for module, level, message in caplog.record_tuples:
        if module == "scout_apm.core.error" and level == logging.DEBUG:
            if message.startswith("Sending error for request: sample_id. Payload: "):
                actual_message = message
                break
    assert actual_message

    assert "ZeroDivisionError" in actual_message
    assert "division by zero" in actual_message
    assert (
        "tests/unit/core/test_error.py:231:in test_monitor_with_logged_payload"
        in actual_message
    )
    assert "sample.app" in actual_message
    assert "DataView" in actual_message
    assert "/test/" in actual_message
