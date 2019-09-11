# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# A constant that represents an "unknown" date. Fallback, and will be rejected
# by the CoreAgent. But important to avoid exceptions if a None timestamp is
# passed to a Command.
INVALID_DATE = datetime(year=2000, month=1, day=1)


class Register(object):
    def __init__(self, *args, **kwargs):
        self.app = kwargs.get("app")
        self.key = kwargs.get("key")
        self.hostname = kwargs.get("hostname")

    def message(self):
        logger.info(
            "Registering with app=%s key=%s host=%s"
            % (self.app, self.key, self.hostname)
        )
        return {
            "Register": {
                "app": self.app,
                "key": self.key,
                "host": self.hostname,
                "language": "python",
                "api_version": "1.0",
            }
        }


class StartSpan(object):
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get("timestamp") or INVALID_DATE
        self.request_id = kwargs.get("request_id")
        self.span_id = kwargs.get("span_id")
        self.parent = kwargs.get("parent")
        self.operation = kwargs.get("operation")

    def message(self):
        return {
            "StartSpan": {
                "timestamp": self.timestamp.isoformat() + "Z",
                "request_id": self.request_id,
                "span_id": self.span_id,
                "parent_id": self.parent,
                "operation": self.operation,
            }
        }


class StopSpan(object):
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get("timestamp") or INVALID_DATE
        self.request_id = kwargs.get("request_id")
        self.span_id = kwargs.get("span_id")

    def message(self):
        return {
            "StopSpan": {
                "timestamp": self.timestamp.isoformat() + "Z",
                "request_id": self.request_id,
                "span_id": self.span_id,
            }
        }


class StartRequest(object):
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get("timestamp") or INVALID_DATE
        self.request_id = kwargs.get("request_id")

    def message(self):
        return {
            "StartRequest": {
                "timestamp": self.timestamp.isoformat() + "Z",
                "request_id": self.request_id,
            }
        }


class FinishRequest(object):
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get("timestamp") or INVALID_DATE
        self.request_id = kwargs.get("request_id")

    def message(self):
        return {
            "FinishRequest": {
                "timestamp": self.timestamp.isoformat() + "Z",
                "request_id": self.request_id,
            }
        }


class TagSpan(object):
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get("timestamp") or INVALID_DATE
        self.request_id = kwargs.get("request_id")
        self.span_id = kwargs.get("span_id")
        self.tag = kwargs.get("tag")
        self.value = kwargs.get("value")

    def message(self):
        return {
            "TagSpan": {
                "timestamp": self.timestamp.isoformat() + "Z",
                "request_id": self.request_id,
                "span_id": self.span_id,
                "tag": self.tag,
                "value": self.value,
            }
        }


class TagRequest(object):
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get("timestamp") or INVALID_DATE
        self.request_id = kwargs.get("request_id")
        self.tag = kwargs.get("tag")
        self.value = kwargs.get("value")

    def message(self):
        return {
            "TagRequest": {
                "timestamp": self.timestamp.isoformat() + "Z",
                "request_id": self.request_id,
                "tag": self.tag,
                "value": self.value,
            }
        }


class ApplicationEvent(object):
    def __init__(self, event_type, event_value, source, timestamp):
        self.event_type = event_type
        self.event_value = event_value
        self.source = source
        self.timestamp = timestamp

    def message(self):
        return {
            "ApplicationEvent": {
                "timestamp": self.timestamp.isoformat() + "Z",
                "event_type": self.event_type,
                "event_value": self.event_value,
                "source": self.source,
            }
        }


class BatchCommand(object):
    def __init__(self, commands):
        self.commands = commands

    def message(self):
        messages = [command.message() for command in self.commands]
        return {"BatchCommand": {"commands": messages}}

    @classmethod
    def from_tracked_request(cls, request):
        # The TrackedRequest must be finished
        commands = []
        commands.append(
            StartRequest(timestamp=request.start_time, request_id=request.req_id)
        )
        for key in request.tags:
            commands.append(
                TagRequest(
                    timestamp=request.start_time,
                    request_id=request.req_id,
                    tag=key,
                    value=request.tags[key],
                )
            )

        for span in request.complete_spans:
            commands.append(
                StartSpan(
                    timestamp=span.start_time,
                    request_id=span.request_id,
                    span_id=span.span_id,
                    parent=span.parent,
                    operation=span.operation,
                )
            )

            for key in span.tags:
                commands.append(
                    TagSpan(
                        timestamp=span.start_time,
                        request_id=request.req_id,
                        span_id=span.span_id,
                        tag=key,
                        value=span.tags[key],
                    )
                )

            commands.append(
                StopSpan(
                    timestamp=span.end_time,
                    request_id=span.request_id,
                    span_id=span.span_id,
                )
            )

        commands.append(
            FinishRequest(timestamp=request.end_time, request_id=request.req_id)
        )

        return BatchCommand(commands)
