import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest

from celery.signals import task_prerun, task_postrun


# TODO: Capture queue.
# https://stackoverflow.com/questions/22385297/how-to-get-the-queue-in-which-a-task-was-run-celery?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
def prerun_callback(sender=None, headers=None, body=None, **kwargs):
    name = kwargs['task'].name

    tr = TrackedRequest.instance()
    tr.mark_real_request()
    span = tr.start_span(operation=('Job/' + name))
    span.tag('queue', 'default')


def postrun_callback(sender=None, headers=None, body=None, **kwargs):
    tr = TrackedRequest.instance()
    tr.stop_span()


def install():
    installed = scout_apm.core.install()
    if installed is False:
        return

    task_prerun.connect(prerun_callback)
    task_postrun.connect(postrun_callback)
