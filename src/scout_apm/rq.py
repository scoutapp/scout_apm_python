# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt

from rq.job import Job as RqJob

import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest

# Custom job class
# rq worker --job-class scout_apm.rq.Job
# Or instantiate queues with `job_class='scout_apm.rq.Job'` or job_class=Job
# or custom Job subclass
# or add JobMixin to your own Job class
# Config via environment variables or custom Job class with Config.set() call
# in the same file
# django-rq should allow using Django config since django.setup() should run as
# part of the management command - need to test that

install_attempted = False
installed = None


def ensure_scout_installed():
    global install_attempted, installed

    if not install_attempted:
        install_attempted = True
        installed = scout_apm.core.install()


class JobMixin(object):
    def __init__(self, *args, **kwargs):
        ensure_scout_installed()
        super(JobMixin, self).__init__(*args, **kwargs)

    def perform(self):
        global installed
        if not installed:
            return super(JobMixin, self).perform()

        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True
        tracked_request.tag("queue", self.origin)
        queue_time = (dt.datetime.utcnow() - self.enqueued_at).total_seconds()
        tracked_request.tag("queue_time", queue_time)
        tracked_request.start_span(operation="Job/{}".format(self.func_name))
        try:
            return super(JobMixin, self).perform()
        except Exception:
            tracked_request.tag("error", "true")
            raise
        finally:
            tracked_request.stop_span()


class Job(JobMixin, RqJob):
    pass
