# coding=utf-8

import os
from collections import namedtuple
from contextlib import contextmanager

import pytest
import redis
from rq import Queue
from rq.version import VERSION

import scout_apm.rq
from scout_apm.api import Config
from scout_apm.compat import kwargs_only
from scout_apm.instruments.redis import ensure_installed

RQ_MAJOR_VERSION = int(VERSION.split(".")[0])


@pytest.fixture(scope="module")
def redis_conn():
    # Copied from test_redis.py
    ensure_installed()
    # e.g. export REDIS_URL="redis://localhost:6379/0"
    if "REDIS_URL" not in os.environ:
        raise pytest.skip("Redis isn't available")
    yield redis.Redis.from_url(os.environ["REDIS_URL"])


def hello():
    return "Hello World!"


def fail():
    raise ValueError("BØØM!")  # non-ASCII


@contextmanager
@kwargs_only
def app_with_scout(redis_conn, scout_config=None):
    """
    Context manager that configures a Huey app with Scout installed.
    """
    # Enable Scout by default in tests.
    if scout_config is None:
        scout_config = {}
    scout_config.setdefault("monitor", True)
    scout_config["core_agent_launch"] = False

    # Reset global state
    scout_apm.rq.install_attempted = False
    scout_apm.rq.installed = None

    # Setup according to https://docs.scoutapm.com/#rq
    # Using job_class argument to Queue
    Config.set(**scout_config)
    queue = Queue(name="myqueue", connection=redis_conn)
    worker = scout_apm.rq.SimpleWorker([queue], connection=queue.connection)

    App = namedtuple("App", ["queue", "worker"])
    try:
        yield App(queue=queue, worker=worker)
    finally:
        Config.reset_all()


def get_job_result(job):
    """Helper wrapper around an old rq API"""
    if VERSION <= "1.13.0":
        return job.result
    return job.return_value()


def expected_span_operations(job_operation):
    """
    rq < 3.0 calls PERSIST on the job key inside Job.perform, so it's captured
    within the job span. rq 3.0 moved it into the worker's pipeline.
    """
    if RQ_MAJOR_VERSION < 3:
        return ["Redis/PERSIST", job_operation]
    return [job_operation]


def test_hello(redis_conn, tracked_requests):
    with app_with_scout(redis_conn=redis_conn) as app:
        job = app.queue.enqueue(hello)
        app.worker.work(burst=True)

    assert job.is_finished
    assert get_job_result(job) == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    task_id = tracked_request.tags["task_id"]
    assert isinstance(task_id, str) and len(task_id) == 36
    assert tracked_request.tags["queue"] == "myqueue"
    assert 0.0 < tracked_request.tags["queue_time"] < 60.0
    assert [
        span.operation for span in tracked_request.complete_spans
    ] == expected_span_operations("Job/tests.integration.test_rq.hello")
    assert tracked_request.operation == "Job/tests.integration.test_rq.hello"


def test_fail(redis_conn, tracked_requests):
    with app_with_scout(redis_conn=redis_conn) as app:
        app.queue.enqueue(fail)
        app.worker.work(burst=True)

    tracked_request = tracked_requests[0]
    task_id = tracked_request.tags["task_id"]
    assert isinstance(task_id, str) and len(task_id) == 36
    assert tracked_request.tags["queue"] == "myqueue"
    assert 0.0 < tracked_request.tags["queue_time"] < 60.0
    assert tracked_request.tags["error"] == "true"
    assert [
        span.operation for span in tracked_request.complete_spans
    ] == expected_span_operations("Job/tests.integration.test_rq.fail")
    assert tracked_request.operation == "Job/tests.integration.test_rq.fail"


def test_no_monitor(redis_conn, tracked_requests):
    with app_with_scout(redis_conn=redis_conn, scout_config={"monitor": False}) as app:
        job = app.queue.enqueue(hello)
        app.worker.work(burst=True)

    assert job.is_finished
    assert get_job_result(job) == "Hello World!"
    assert tracked_requests == []
