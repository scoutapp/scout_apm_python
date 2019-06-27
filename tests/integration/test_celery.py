# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from celery import Celery

import scout_apm.celery
from scout_apm.api import Config


@contextmanager
def app_with_scout(config=None):
    """
    Context manager that configures and installs the Scout plugin for Bottle.

    """
    # Enable Scout by default in tests.
    if config is None:
        config = {"monitor": True}

    # Disable running the agent.
    config["core_agent_launch"] = False

    app = Celery("tasks", broker="memory://")

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


def test_hello(tracked_requests):
    with app_with_scout() as app:
        result = app.tasks["tests.integration.test_celery.hello"].apply()

    assert result.result == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_celery.hello"
    assert span.tags["queue"] == "default"


def test_no_monitor(tracked_requests):
    # With an empty config, "monitor" defaults to False.
    with app_with_scout({}) as app:
        result = app.tasks["tests.integration.test_celery.hello"].apply()

    assert result.result == "Hello World!"
    assert tracked_requests == []
