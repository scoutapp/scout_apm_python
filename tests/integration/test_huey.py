# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from contextlib import contextmanager

import pytest
from huey import MemoryHuey
from huey.exceptions import CancelExecution, HueyException, RetryTask, TaskException

from scout_apm.api import Config
from scout_apm.huey import attach_scout


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

    huey = MemoryHuey(immediate=True)

    @huey.task()
    @huey.lock_task("hello")
    def hello():
        return "Hello World!"

    @huey.task()
    def retry_once():
        if not retry_once._did_retry:
            retry_once._did_retry = True
            raise RetryTask()
        return "Done."

    retry_once._did_retry = False

    @huey.task()
    def fail():
        raise ValueError("BØØM!")  # non-ASCII

    # Setup according to https://docs.scoutapm.com/#huey
    Config.set(**scout_config)
    attach_scout(huey)

    App = namedtuple("App", ["huey", "hello", "retry_once", "fail"])
    try:
        yield App(huey=huey, hello=hello, retry_once=retry_once, fail=fail)
    finally:
        Config.reset_all()


def test_hello(tracked_requests):
    with app_with_scout() as app:
        result = app.hello()
        value = result(blocking=True, timeout=1)

    assert value == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert "task_id" in tracked_request.tags
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_huey.hello"


def test_retry_once(tracked_requests):
    with app_with_scout() as app:
        result = app.retry_once()
        value = result(blocking=True, timeout=1)

    assert value == "Done."
    assert len(tracked_requests) == 2
    tracked_request = tracked_requests[0]
    assert "task_id" in tracked_request.tags
    assert tracked_request.tags["retrying"] is True
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_huey.retry_once"


def test_fail(tracked_requests):
    with app_with_scout() as app:
        result = app.fail()
        with pytest.raises(TaskException):
            result(blocking=True, timeout=1)

    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["error"] == "true"
    assert "task_id" in tracked_request.tags
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_huey.fail"


def test_cancelled(tracked_requests):
    with app_with_scout() as app:

        @app.huey.pre_execute()
        def cancel_all_tasks(task):
            raise CancelExecution()

        result = app.hello()

        with pytest.raises(HueyException) as excinfo:
            result(blocking=True, timeout=0.1)

    assert excinfo.value.args == ("timed out waiting for result",)
    assert tracked_requests == []


def test_locked(tracked_requests):
    with app_with_scout() as app:
        with app.huey.lock_task("hello"):
            result = app.hello()

            with pytest.raises(TaskException) as excinfo:
                result(blocking=True, timeout=0.1)

    assert excinfo.value.metadata["error"].startswith("TaskLockedException")
    assert tracked_requests == []


def test_no_monitor(tracked_requests):
    with app_with_scout(scout_config={"monitor": False}) as app:
        result = app.hello()
        value = result(blocking=True, timeout=1)

    assert value == "Hello World!"
    assert tracked_requests == []
