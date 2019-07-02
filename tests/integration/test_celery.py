# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

import celery
import pytest
from celery.signals import setup_logging

import scout_apm.celery
from scout_apm.api import Config

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
def app_with_scout(app=None, config=None):
    """
    Context manager that configures a Celery app with Scout installed.
    """
    if app is None:
        app = celery.Celery("tasks", broker="memory://")

    # Enable Scout by default in tests.
    if config is None:
        config = {"monitor": True}

    # Disable running the agent.
    config["core_agent_launch"] = False

    @app.task
    def hello():
        return "Hello World!"

    # Setup according to https://docs.scoutapm.com/#celery
    Config.set(**config)
    scout_apm.celery.install()

    try:
        yield app
    finally:
        scout_apm.celery.uninstall()
        # Reset Scout configuration.
        Config.reset_all()


def test_hello_eager(tracked_requests):
    with app_with_scout() as app:
        result = app.tasks["tests.integration.test_celery.hello"].apply()

    assert result.result == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["is_eager"] is True
    assert tracked_request.tags["exchange"] == "unknown"
    assert tracked_request.tags["routing_key"] == "unknown"
    assert tracked_request.tags["queue"] == "unknown"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_celery.hello"


@skip_unless_celery_4_plus
def test_hello_worker(celery_app, celery_worker, tracked_requests):
    with app_with_scout(app=celery_app) as app:
        result = app.tasks["tests.integration.test_celery.hello"].delay().get()

    assert result == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["is_eager"] is False
    assert tracked_request.tags["exchange"] == ""
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


def test_no_monitor(tracked_requests):
    # With an empty config, "monitor" defaults to False.
    with app_with_scout(config={}) as app:
        result = app.tasks["tests.integration.test_celery.hello"].apply()

    assert result.result == "Hello World!"
    assert tracked_requests == []
