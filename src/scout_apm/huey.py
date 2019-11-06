# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from huey.exceptions import RetryTask, TaskLockedException
from huey.signals import SIGNAL_CANCELED

from scout_apm.core.tracked_request import TrackedRequest


def attach_scout(huey):
    huey.pre_execute()(scout_on_pre_execute)
    huey.post_execute()(scout_on_post_execute)
    huey.signal(SIGNAL_CANCELED)(scout_on_cancelled)


def scout_on_pre_execute(task):
    tracked_request = TrackedRequest.instance()

    tracked_request.tag("task_id", task.id)

    operation = "Job/{}.{}".format(task.__module__, task.__class__.__name__)
    tracked_request.start_span(operation=operation)


def scout_on_post_execute(task, task_value, exception):
    tracked_request = TrackedRequest.instance()
    if exception is None:
        tracked_request.is_real_request = True
    elif isinstance(exception, TaskLockedException):
        pass
    elif isinstance(exception, RetryTask):
        tracked_request.is_real_request = True
        tracked_request.tag("retrying", True)
    else:
        tracked_request.is_real_request = True
        tracked_request.tag("error", "true")
    tracked_request.stop_span()


def scout_on_cancelled(signal, task, exc=None):
    # In the case of a cancelled signal, Huey doesn't run the post_execute
    # handler, so we need to tidy up
    TrackedRequest.instance().stop_span()
