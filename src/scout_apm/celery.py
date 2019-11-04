# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt

from celery.signals import before_task_publish, task_postrun, task_prerun

import scout_apm.core
from scout_apm.compat import datetime_to_timestamp
from scout_apm.core.tracked_request import TrackedRequest


def before_publish_callback(headers=None, properties=None, **kwargs):
    if "scout_task_start" not in headers:
        headers["scout_task_start"] = datetime_to_timestamp(dt.datetime.utcnow())


def prerun_callback(task=None, **kwargs):
    tracked_request = TrackedRequest.instance()
    tracked_request.is_real_request = True

    start = getattr(task.request, "scout_task_start", None)
    if start is not None:
        now = datetime_to_timestamp(dt.datetime.utcnow())
        try:
            queue_time = now - start
        except TypeError:
            pass
        else:
            tracked_request.tag("queue_time", queue_time)

    task_id = getattr(task.request, "id", None)
    if task_id:
        tracked_request.tag("task_id", task_id)
    parent_task_id = getattr(task.request, "parent_id", None)
    if parent_task_id:
        tracked_request.tag("parent_task_id", parent_task_id)

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

    before_task_publish.connect(before_publish_callback)
    task_prerun.connect(prerun_callback)
    task_postrun.connect(postrun_callback)


def uninstall():
    before_task_publish.disconnect(before_publish_callback)
    task_prerun.disconnect(prerun_callback)
    task_postrun.disconnect(postrun_callback)
