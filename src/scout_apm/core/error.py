# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

try:
    from html import escape
except ImportError:
    from cgi import escape

import requests

from scout_apm.core.backtrace import capture
from scout_apm.core.config import scout_config
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import filter_element


class ErrorMonitor(object):
    @classmethod
    def send(
        cls,
        exception,
        path,
        params=None,
        session=None,
        environment=None,
        request_components=None,
    ):

        if not scout_config.value("errors_enabled"):
            return

        if isinstance(exception, scout_config.value("errors_ignored_exceptions")):
            return

        traceback = sys.exc_info()[2]
        tags = TrackedRequest.instance().tags if scout_config.value("monitor") else None

        message = {
            "exception_class": exception.__class__,
            "message": exception,
            "request_uri": path,
            "request_params": filter_element("", params) if params else None,
            "request_session": filter_element("", session) if session else None,
            "environment": filter_element("", environment) if environment else None,
            "trace": capture(traceback.tb_frame, apply_filter=False),
            "request_components": request_components,
            "context": tags,
            "host": scout_config.value("hostname"),
            "revision_sha": scout_config.value("revision_sha"),
        }

        # send via API
        response = cls._push(message)  # noqa

    @classmethod
    def _push(cls, message):
        params = {
            "key": scout_config.value("key"),
            "app": escape(scout_config.value("name"), quote=False),
        }
        headers = {
            "Agent-Hostname": scout_config.value("hostname"),
            "Content-Type": "application/octet-stream",
        }
        return requests.post(
            scout_config.value("errors_host/apps/error.scout"),
            params=params,
            data=message,
            headers=headers,
        )
