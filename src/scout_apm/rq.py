# coding=utf-8

import datetime as dt
import logging

import wrapt
from rq import SimpleWorker as RqSimpleWorker
from rq import Worker as RqWorker
from rq.job import Job
from rq.worker import HerokuWorker as RqHerokuWorker

import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest

install_attempted = False
installed = None

logger = logging.getLogger(__name__)


def ensure_scout_installed():
    global install_attempted, installed

    if not install_attempted:
        install_attempted = True
        installed = scout_apm.core.install()


class WorkerMixin(object):
    def __init__(self, *args, **kwargs):
        global installed
        ensure_scout_installed()
        if installed:
            ensure_job_instrumented()
        super(WorkerMixin, self).__init__(*args, **kwargs)


class Worker(WorkerMixin, RqWorker):
    pass


class SimpleWorker(WorkerMixin, RqSimpleWorker):
    pass


class HerokuWorker(WorkerMixin, RqHerokuWorker):
    pass


job_instrumented = False


def ensure_job_instrumented():
    global job_instrumented
    if job_instrumented:
        return
    job_instrumented = True
    Job.perform = wrap_perform(Job.perform)

    try:
        from rq.serializers import DefaultSerializer
        import pickle

        if getattr(DefaultSerializer, "dumps", None) is pickle.dumps:
            logger.warning(
                "RQ is using the default pickle serializer, which is vulnerable to "
                "Remote Code Execution (RCE) via Redis (CWE-502). Consider switching "
                "to a safer serializer like rq.serializers.JSONSerializer. "
                "See https://github.com/rq/rq/issues/2389 for details."
            )
    except Exception:
        pass


@wrapt.decorator
def wrap_perform(wrapped, instance, args, kwargs):
    global installed
    if not installed:
        return wrapped(*args, **kwargs)

    tracked_request = TrackedRequest.instance()
    tracked_request.is_real_request = True
    tracked_request.tag("task_id", instance.id)
    tracked_request.tag("queue", instance.origin)
    # rq strips tzinfo from enqueued_at during serde in at least some cases
    # internally everything uses UTC naive datetimes, so we operate on that
    # assumption here.
    if instance.enqueued_at.tzinfo is None:
        queued_at = instance.enqueued_at.replace(tzinfo=dt.timezone.utc)
    else:
        queued_at = instance.enqueued_at
    queue_time = (dt.datetime.now(dt.timezone.utc) - queued_at).total_seconds()
    tracked_request.tag("queue_time", queue_time)
    operation = "Job/{}".format(instance.func_name)
    tracked_request.operation = operation
    with tracked_request.span(operation=operation):
        try:
            return wrapped(*args, **kwargs)
        except Exception:
            tracked_request.tag("error", "true")
            raise
