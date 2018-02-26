from __future__ import absolute_import

# Python Modules
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class StartSpan:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.request_id = kwargs.get('request_id', None)
        self.span_id = kwargs.get('span_id', None)
        self.parent = kwargs.get('parent', None)
        self.operation = kwargs.get('operation', None)

    def message(self):
        return {'StartSpan': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'span_id': self.span_id,
            'parent_id': self.parent,
            'operation': self.operation,
        }}


class StopSpan:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.request_id = kwargs.get('request_id', None)
        self.span_id = kwargs.get('span_id', None)

    def message(self):
        return {'StopSpan': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'span_id': self.span_id,
        }}


class StartRequest:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.request_id = kwargs.get('request_id', None)

    def message(self):
        return {'StartRequest': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
        }}


class FinishRequest:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.request_id = kwargs.get('request_id', None)

    def message(self):
        return {'FinishRequest': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
        }}


class TagSpan:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.request_id = kwargs.get('request_id', None)
        self.span_id = kwargs.get('span_id', None)
        self.tag = kwargs.get('tag', None)
        self.value = kwargs.get('value', None)

    def message(self):
        return {'TagSpan': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'span_id': self.span_id,
            'tag': self.tag,
            'value': self.value,
        }}


class TagRequest:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.request_id = kwargs.get('request_id', None)
        self.tag = kwargs.get('tag', None)
        self.value = kwargs.get('value', None)

    def message(self):
        return {'TagRequest': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'tag': self.tag,
            'value': self.value,
        }}


class CoreAgentVersion:
    def message(self):
        return {'CoreAgentVersion': {}}


class CoreAgentVersionResponse:
    def __init__(self, message):
        self.loaded = json.loads(message)
        self.version = self.loaded['CoreAgentVersion']['version']


class BatchedCommand:
    def __init__(self, commands):
        self.commands = commands

    def message(self):
        messages = list(map(lambda cmd: cmd.message(), self.commands))
        return {'BatchedCommand': messages}

    @classmethod
    def from_tracked_request(cls, request):
        commands = []
        # Request Start
        commands.append(StartRequest(timestamp=request.start_time,
                                     request_id=request.req_id))
        # Request Tags
        for key in request.tags:
            commands.append(TagRequest(timestamp=request.start_time,
                                       request_id=request.req_id,
                                       tag=key,
                                       value=request.tags[key]))
        # Spans
        for span in request.spans:
            # Span Start
            commands.append(StartSpan(timestamp=span.start_time,
                                      request_id=span.request_id,
                                      span_id=span.span_id,
                                      parent=span.parent,
                                      operation=span.operation))
            # Span Tags
            for key in span.tags:
                commands.append(TagSpan(timestamp=span.start_time,
                                        request_id=request.req_id,
                                        span_id=span.span_id,
                                        tag=key,
                                        value=span.tags[key]))
            # Span End
            commands.append(StopSpan(timestamp=span.end_time,
                                     request_id=span.request_id,
                                     span_id=span.span_id))
        # Request Finish
        commands.append(FinishRequest(timestamp=request.end_time,
                                      request_id=request.req_id))
        return BatchedCommand(commands)

