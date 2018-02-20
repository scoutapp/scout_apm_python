from __future__ import absolute_import

# Python Modules
import datetime
import json
import logging

logger = logging.getLogger(__name__)


class StartSpan:
    def __init__(self, request_id, span_id, parent, operation):
        self.timestamp = datetime.datetime.utcnow()
        self.request_id = request_id
        self.span_id = span_id
        self.parent = parent
        self.operation = operation

    def message(self):
        return {'StartSpan': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'span_id': self.span_id,
            'parent_id': self.parent,
            'operation': self.operation,
        }}


class StopSpan:
    def __init__(self, request_id, span_id):
        self.timestamp = datetime.datetime.utcnow()
        self.request_id = request_id
        self.span_id = span_id

    def message(self):
        return {'StopSpan': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'span_id': self.span_id,
        }}


class StartRequest:
    def __init__(self, request_id):
        self.timestamp = datetime.datetime.utcnow()
        self.request_id = request_id

    def message(self):
        return {'StartRequest': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
        }}


class FinishRequest:
    def __init__(self, request_id):
        self.timestamp = datetime.datetime.utcnow()
        self.request_id = request_id

    def message(self):
        return {'FinishRequest': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
        }}


class TagSpan:
    def __init__(self, request_id, span_id, tag, value):
        self.timestamp = datetime.datetime.utcnow()
        self.request_id = request_id
        self.span_id = span_id
        self.tag = tag
        self.value = value

    def message(self):
        return {'TagSpan': {
            'moment': self.timestamp.isoformat() + 'Z',
            'request_id': self.request_id,
            'span_id': self.span_id,
            'tag': self.tag,
            'value': self.value,
        }}


class TagRequest:
    def __init__(self, request_id, tag, value):
        self.timestamp = datetime.datetime.utcnow()
        self.request_id = request_id
        self.tag = tag
        self.value = value

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


class CoreAgentShutdown:
    def message(self):
        return {'CoreAgentShutdown': {}}


class BatchedCommand:
    def __init__(self, commands):
        self.commands = commands

    def message(self):
        messages = map(lambda cmd: cmd.message(), self.commands)
        return {'BatchedCommand': messages}
