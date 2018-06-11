from __future__ import absolute_import

# Python Modules
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

# A constant that represents an "unknown" date. Fallback, and will be rejected
# by the CoreAgent. But important to avoid exceptions if a None timestamp is
# passed to a Command.
INVALID_DATE = datetime(year=2000, month=1, day=1)


class Register:
    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('app', None)
        self.key = kwargs.get('key', None)

    def message(self):
        logging.info('Registering with app=%s key=%s' % (self.app, self.key))
        return {'Register': {
            'app': self.app,
            'key': self.key,
            'language': 'python',
            'api_version': '1.0',
        }}


class StartSpan:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp') or INVALID_DATE
        self.request_id = kwargs.get('request_id', None)
        self.span_id = kwargs.get('span_id', None)
        self.parent = kwargs.get('parent', None)
        self.operation = kwargs.get('operation', None)

    def message(self):
        return {'StartSpan': {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'span_id': self.span_id,
            'parent_id': self.parent,
            'operation': self.operation,
        }}


class StopSpan:
    def __init__(self, *args, **kwargs):
        self.request_id = kwargs.get('request_id', None)
        self.span_id = kwargs.get('span_id', None)
        self.timestamp = kwargs.get('timestamp') or INVALID_DATE

    def message(self):
        return {'StopSpan': {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'span_id': self.span_id,
        }}


class StartRequest:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp') or INVALID_DATE
        self.request_id = kwargs.get('request_id', None)

    def message(self):
        return {'StartRequest': {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
        }}


class FinishRequest:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp') or INVALID_DATE
        self.request_id = kwargs.get('request_id', None)

    def message(self):
        return {'FinishRequest': {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
        }}


class TagSpan:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp') or INVALID_DATE
        self.request_id = kwargs.get('request_id', None)
        self.span_id = kwargs.get('span_id', None)
        self.tag = kwargs.get('tag', None)
        self.value = kwargs.get('value', None)

    def message(self):
        return {'TagSpan': {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'span_id': self.span_id,
            'tag': self.tag,
            'value': self.value,
        }}


class TagRequest:
    def __init__(self, *args, **kwargs):
        self.timestamp = kwargs.get('timestamp') or INVALID_DATE
        self.request_id = kwargs.get('request_id', None)
        self.tag = kwargs.get('tag', None)
        self.value = kwargs.get('value', None)

    def message(self):
        return {'TagRequest': {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'tag': self.tag,
            'value': self.value,
        }}


class ApplicationEvent:
    def __init__(self, *args, **kwargs):
        self.event_type = kwargs.get('event_type', '')
        self.event_value = kwargs.get('event_value', '')
        self.timestamp = kwargs.get('timestamp') or INVALID_DATE
        self.source = kwargs.get('source', '')

    def message(self):
        return {'ApplicationEvent': {
                    'event_type':  self.event_type,
                    'event_value': self.event_value,
                    'timestamp': self.timestamp.isoformat() + 'Z',
                    'source': self.source,
        }}


class CoreAgentVersion:
    def message(self):
        return {'CoreAgentVersion': {}}


class CoreAgentVersionResponse:
    def __init__(self, message):
        self.loaded = json.loads(message)
        self.version = self.loaded['CoreAgentVersion']['version']


class BatchCommand:
    def __init__(self, commands):
        self.commands = commands

    def message(self):
        messages = list(map(lambda cmd: cmd.message(), self.commands))
        return {'BatchCommand': {'commands': messages}}

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
        for span in request.complete_spans:
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
            if span.end_time is None:
                logger.debug("Invalid Request, span_id: %s had a None end_time", span.span_id)
                return None

            commands.append(StopSpan(timestamp=span.end_time,
                                     request_id=span.request_id,
                                     span_id=span.span_id))
        # Request Finish
        if request.end_time is None:
            logger.debug("Invalid Request, request_id: %s had a None end_time", request.req_id)
            return None

        commands.append(FinishRequest(timestamp=request.end_time,
                                      request_id=request.req_id))

        return BatchCommand(commands)
