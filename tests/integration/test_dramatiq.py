# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from collections import namedtuple
from contextlib import contextmanager

import pytest

if sys.version_info < (3, 5):  # Minimum version dramatiq should be installable on
    pytest.skip(
        "Dramatiq not installable on this Python version", allow_module_level=True
    )
else:
    import dramatiq
    from dramatiq.brokers.stub import StubBroker

    from scout_apm.api import Config
    from scout_apm.dramatiq import ScoutMiddleware


@contextmanager
def app_with_scout(config=None):
    """
    Context manager that configures a Dramatiq app with Scout middleware
    installed.
    """
    # Enable Scout by default in tests.
    if config is None:
        config = {"monitor": True}

    # Disable running the agent.
    config["core_agent_launch"] = False

    broker = StubBroker()
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)

    @dramatiq.actor(max_retries=0)
    def hello():
        return "Hello World!"

    @dramatiq.actor(max_retries=0)
    def fail():
        raise ValueError("BØØM!")  # non-ASCII

    worker = dramatiq.Worker(broker, worker_timeout=0)

    # Setup according to https://docs.scoutapm.com/#dramatiq
    Config.set(**config)
    broker.add_middleware(ScoutMiddleware(), before=broker.middleware[0].__class__)
    worker.start()

    App = namedtuple("App", ["broker", "worker", "hello", "fail"])
    try:
        yield App(broker=broker, worker=worker, hello=hello, fail=fail)
    finally:
        worker.stop()
        # Reset Scout configuration.
        Config.reset_all()


def test_hello(tracked_requests):
    with app_with_scout() as app:
        app.hello.send()
        app.broker.join(app.hello.queue_name)
        app.worker.join()

    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["queue"] == "default"
    assert "message_id" in tracked_request.tags
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/hello"


def test_fail(tracked_requests):
    with app_with_scout() as app:
        app.fail.send()
        app.broker.join(app.fail.queue_name)
        app.worker.join()

    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["queue"] == "default"
    assert "message_id" in tracked_request.tags
    assert tracked_request.tags["error"] == "true"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/fail"


def test_not_installed(tracked_requests):
    with app_with_scout() as app:
        app.broker.middleware[0]._do_nothing = True
        app.hello.send()
        app.broker.join(app.fail.queue_name)
        app.worker.join()

    assert tracked_requests == []


def test_skipped(tracked_requests):
    class SkipMiddleware(dramatiq.Middleware):
        def before_process_message(self, broker, message):
            raise dramatiq.middleware.SkipMessage()

    with app_with_scout() as app:
        app.broker.add_middleware(SkipMiddleware(), after=ScoutMiddleware)
        app.hello.send()
        app.broker.join(app.hello.queue_name)
        app.worker.join()

    assert tracked_requests == []
