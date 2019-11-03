# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import dramatiq

import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest


class ScoutMiddleware(dramatiq.Middleware):
    def __init__(self):
        installed = scout_apm.core.install()
        self._do_nothing = not installed

    def before_process_message(self, broker, message):
        if self._do_nothing:
            return
        tracked_request = TrackedRequest.instance()
        tracked_request.tag("queue", message.queue_name)
        tracked_request.tag("message_id", message.message_id)
        tracked_request.start_span(operation="Job/" + message.actor_name)

    def after_process_message(self, broker, message, result=None, exception=None):
        if self._do_nothing:
            return
        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True
        if exception:
            tracked_request.tag("error", "true")
        tracked_request.stop_span()

    def after_skip_message(self, broker, message):
        """
        The message was skipped by another middleware raising SkipMessage.
        Stop the span and thus the request, it won't have been marked as real
        so that's alright.
        """
        if self._do_nothing:
            return
        tracked_request = TrackedRequest.instance()
        tracked_request.stop_span()
