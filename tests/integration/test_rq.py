# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from contextlib import contextmanager

import pytest
from fakeredis import FakeStrictRedis
from rq import Queue

from scout_apm import compat, rq
from scout_apm.api import Config


def hello():
    return "Hello World!"


def fail():
    raise ValueError("BØØM!")  # non-ASCII


@contextmanager
def app_with_scout(scout_config=None):
    """
    Context manager that configures a Huey app with Scout installed.
    """
    # Enable Scout by default in tests.
    if scout_config is None:
        scout_config = {}
    scout_config.setdefault("monitor", True)
    scout_config["core_agent_launch"] = False

    # Reset global state
    rq.install_attempted = False
    rq.installed = None

    # Setup according to https://docs.scoutapm.com/#rq
    # Using job_class argument to Queue
    queue = Queue(
        name="myqueue",
        is_async=False,
        connection=FakeStrictRedis(),
        job_class="scout_apm.rq.Job",
    )
    Config.set(**scout_config)

    App = namedtuple("App", ["queue"])
    try:
        yield App(queue=queue)
    finally:
        Config.reset_all()


def test_hello(tracked_requests):
    with app_with_scout() as app:
        job = app.queue.enqueue(hello)

    assert job.is_finished
    assert job.result == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    task_id = tracked_request.tags["task_id"]
    assert isinstance(task_id, compat.string_type) and len(task_id) == 36
    assert tracked_request.tags["queue"] == "myqueue"
    assert 0.0 < tracked_request.tags["queue_time"] < 60.0
    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Redis/PERSIST"
    assert (
        tracked_request.complete_spans[1].operation
        == "Job/tests.integration.test_rq.hello"
    )


def test_fail(tracked_requests):
    with app_with_scout() as app, pytest.raises(ValueError):
        app.queue.enqueue(fail)

    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    task_id = tracked_request.tags["task_id"]
    assert isinstance(task_id, compat.string_type) and len(task_id) == 36
    assert tracked_request.tags["queue"] == "myqueue"
    assert 0.0 < tracked_request.tags["queue_time"] < 60.0
    assert tracked_request.tags["error"] == "true"
    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Redis/PERSIST"
    assert (
        tracked_request.complete_spans[1].operation
        == "Job/tests.integration.test_rq.fail"
    )


def test_no_monitor(tracked_requests):
    with app_with_scout(scout_config={"monitor": False}) as app:
        job = app.queue.enqueue(hello)

    assert job.is_finished
    assert job.result == "Hello World!"
    assert tracked_requests == []
