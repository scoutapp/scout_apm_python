# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from contextlib import contextmanager

from fakeredis import FakeStrictRedis
from rq import Queue

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

    queue = Queue(is_async=False, connection=FakeStrictRedis())

    # Setup according to https://docs.scoutapm.com/#rq
    Config.set(**scout_config)
    ...

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
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_rq.hello"
