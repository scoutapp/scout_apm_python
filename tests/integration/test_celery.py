# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from contextlib import contextmanager
from types import SimpleNamespace

import celery
import pytest
from celery.signals import setup_logging
from django.core.exceptions import ImproperlyConfigured

import scout_apm.celery
from scout_apm.api import Config
from scout_apm.compat import kwargs_only
from scout_apm.core.config import scout_config
from tests.compat import mock

# http://docs.celeryproject.org/en/latest/userguide/testing.html#py-test
skip_unless_celery_4_plus = pytest.mark.skipif(
    celery.VERSION < (4, 0), reason="pytest fixtures added in Celery 4.0"
)


@setup_logging.connect
def do_nothing(**kwargs):
    # Just by connecting to this signal, we prevent Celery from setting up
    # logging - and stop it from interfering with global state
    # http://docs.celeryproject.org/en/v4.3.0/userguide/signals.html#setup-logging
    pass


@contextmanager
@kwargs_only
def app_with_scout(celery_config=None, app=None, config=None):
    """
    Context manager that configures a Celery app with Scout installed.
    """
    if app is None:
        app = celery.Celery("tasks", broker="memory://")

    if celery_config is not None:
        app.config_from_object(celery_config)

    # Enable Scout by default in tests.
    if config is None:
        config = {"monitor": True}

    # Disable running the agent.
    config["core_agent_launch"] = False

    @app.task
    def hello():
        return "Hello World!"

    @app.task
    def crash(foo, spam=None):
        raise ValueError("Boom!")

    # Setup according to https://docs.scoutapm.com/#celery
    Config.set(**config)
    scout_apm.celery.install(app)

    try:
        yield app
    finally:
        scout_apm.celery.uninstall()
        # Reset Scout configuration.
        Config.reset_all()


def test_configuration_copied():
    celery_config = SimpleNamespace(SCOUT_IGNORE=["/foobar/"])
    with app_with_scout(celery_config=celery_config):
        assert scout_config.value("ignore") == ["/foobar/"]


def test_hello_eager(tracked_requests):
    with app_with_scout() as app:
        result = app.tasks["tests.integration.test_celery.hello"].apply()

    assert result.result == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert "task_id" in tracked_request.tags
    assert tracked_request.tags["is_eager"] is True
    if celery.VERSION < (5, 1):
        assert tracked_request.tags["exchange"] == "unknown"
        assert tracked_request.tags["priority"] == "unknown"
        assert tracked_request.tags["routing_key"] == "unknown"
    else:
        assert tracked_request.tags["exchange"] is None
        assert tracked_request.tags["priority"] is None
        assert tracked_request.tags["routing_key"] is None
    assert tracked_request.tags["queue"] == "unknown"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_celery.hello"


def test_error_task(tracked_requests):
    with app_with_scout() as app:
        result = app.tasks["tests.integration.test_celery.crash"].si(None).apply()

    assert isinstance(result.result, ValueError)
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_celery.crash"
    assert tracked_request.tags["error"]


def test_error_task_error_monitor(error_monitor_errors, mock_get_safe_settings):
    mock_get_safe_settings.return_value = {"setting1": "value"}
    with app_with_scout(config={"errors_enabled": True, "monitor": True}) as app:
        result = (
            app.tasks["tests.integration.test_celery.crash"].si("arg1", spam=2).apply()
        )

    assert isinstance(result.result, ValueError)

    assert len(error_monitor_errors) == 1
    error = error_monitor_errors[0]
    filepath, line, func_str = error["trace"][0].split(":")
    assert filepath.endswith("tests/integration/test_celery.py")
    # The line number changes between python versions. Make sure it's not empty.
    assert line
    assert func_str == "in crash"
    assert error["exception_class"] == "ValueError"
    assert error["message"] == "Boom!"
    assert error["request_components"] == {
        "module": None,
        "controller": "tests.integration.test_celery.crash",
        "action": None,
    }
    assert error["context"]["custom_params"] == {
        "celery": {
            "args": ("arg1",),
            "kwargs": {"spam": 2},
            "task_id": result.task_id,
        },
    }


@pytest.fixture
def mock_get_safe_settings():
    """We're unable to mock.patch the function so monkey-patch it."""
    original = scout_apm.celery.get_safe_settings
    scout_apm.celery.get_safe_settings = mock.Mock()
    yield scout_apm.celery.get_safe_settings
    scout_apm.celery.get_safe_settings = original


@pytest.mark.parametrize(
    "thrown, log_starts_with",
    [
        [
            ImproperlyConfigured("invalid"),
            "Celery integration does not have django configured properly: "
            "ImproperlyConfigured",
        ],
        [
            Exception("other"),
            "Celery task_failure callback exception: Exception",
        ],
    ],
)
def test_error_task_error_monitor_exception(
    thrown, log_starts_with, mock_get_safe_settings, error_monitor_errors, caplog
):
    mock_get_safe_settings.side_effect = thrown
    with app_with_scout(config={"errors_enabled": True, "monitor": True}) as app:
        result = app.tasks["tests.integration.test_celery.crash"].si(None).apply()

    assert isinstance(result.result, ValueError)

    assert len(error_monitor_errors) == 1
    error = error_monitor_errors[0]
    assert error["context"]["custom_params"] == {
        "celery": {
            "args": (None,),
            "kwargs": {},
            "task_id": result.task_id,
        },
    }
    assert error["request_components"] == {
        "module": None,
        "controller": "tests.integration.test_celery.crash",
        "action": None,
    }
    actual_debugs = [
        log
        for source, level, log in caplog.record_tuples
        if source == "scout_apm.celery" and level == logging.DEBUG
    ]
    assert len(actual_debugs) == 1
    assert actual_debugs[0].startswith(log_starts_with)


@mock.patch("scout_apm.celery.get_safe_settings", False)
@mock.patch("scout_apm.celery.ErrorMonitor.send")
def test_celery_task_failure_callback_tracback_fallback(
    mock_send, mock_get_safe_settings, tracked_request
):
    """
    Verify that when the traceback param is a string, it uses einfo.tb
    """
    exception = Exception()
    mock_sender = mock.Mock()
    mock_sender.name = "test"
    scout_apm.celery.task_failure_callback(
        sender=mock_sender,
        task_id=None,
        exception=exception,
        args=None,
        kwargs=None,
        traceback="spam",
        einfo=mock.Mock(tb="traceback"),
    )
    mock_send.assert_called_once_with(
        (Exception, exception, "traceback"),
        environment=None,
        custom_params={
            "celery": {
                "task_id": None,
                "args": None,
                "kwargs": None,
            }
        },
        custom_controller="test",
    )


@skip_unless_celery_4_plus
def test_hello_worker(celery_app, celery_worker, tracked_requests):
    with app_with_scout(app=celery_app) as app:
        result = app.tasks["tests.integration.test_celery.hello"].delay().get()

    assert result == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert "task_id" in tracked_request.tags
    assert tracked_request.tags["is_eager"] is False
    assert tracked_request.tags["exchange"] == ""
    assert tracked_request.tags["priority"] == 0
    assert tracked_request.tags["routing_key"] == "celery"
    assert tracked_request.tags["queue"] == "unknown"
    assert (
        0.0 <= tracked_request.tags["queue_time"] < 60.0
    )  # Assume test took <60 seconds
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_celery.hello"


@skip_unless_celery_4_plus
def test_hello_worker_header_preset(celery_app, celery_worker, tracked_requests):
    with app_with_scout(app=celery_app) as app:
        result = (
            app.tasks["tests.integration.test_celery.hello"]
            .apply_async(headers={"scout_task_start": "an evil string"})
            .get()
        )

    assert result == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_celery.hello"
    assert "queue_time" not in span.tags


@skip_unless_celery_4_plus
def test_hello_worker_chain(celery_app, celery_worker, tracked_requests):
    with app_with_scout(app=celery_app) as app:
        hello = app.tasks["tests.integration.test_celery.hello"]
        result = (hello.si() | hello.si()).apply_async().get()

    assert result == "Hello World!"
    assert len(tracked_requests) == 2
    assert [t.complete_spans[0].operation for t in tracked_requests] == [
        "Job/tests.integration.test_celery.hello",
        "Job/tests.integration.test_celery.hello",
    ]
    assert "parent_task_id" not in tracked_requests[0].tags
    first_task_id = tracked_requests[0].tags["task_id"]
    assert tracked_requests[1].tags["parent_task_id"] == first_task_id


def test_no_monitor(tracked_requests):
    # With an empty config, "monitor" defaults to False.
    with app_with_scout(config={}) as app:
        result = app.tasks["tests.integration.test_celery.hello"].apply()

    assert result.result == "Hello World!"
    assert tracked_requests == []
