# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from celery.signals import task_postrun, task_prerun

import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest


def prerun_callback(task=None, **kwargs):
    tracked_request = TrackedRequest.instance()
    tracked_request.mark_real_request()

    delivery_info = task.request.delivery_info
    tracked_request.tag("is_eager", delivery_info.get("is_eager", False))
    tracked_request.tag("exchange", delivery_info.get("exchange", "unknown"))
    tracked_request.tag("routing_key", delivery_info.get("routing_key", "unknown"))
    tracked_request.tag("queue", delivery_info.get("queue", "unknown"))

    tracked_request.start_span(operation=("Job/" + task.name))


def postrun_callback(task=None, **kwargs):
    tracked_request = TrackedRequest.instance()
    tracked_request.stop_span()


def install():
    installed = scout_apm.core.install()
    if not installed:
        return

    task_prerun.connect(prerun_callback)
    task_postrun.connect(postrun_callback)


def uninstall():
    task_prerun.disconnect(prerun_callback)
    task_postrun.disconnect(postrun_callback)
