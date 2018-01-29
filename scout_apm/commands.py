import json


class StartSpan:
    def __init__(self, request_id, span_id, parent, operation):
        print('StartSpan Command')
        self.request_id = request_id
        self.span_id = span_id
        self.parent = parent
        self.operation = operation

    def message(self):
        return {
            'StartSpan': {
                'request_id': self.request_id,
                'span_id': self.span_id,
                'parent_id': self.parent,
                'operation': self.operation,
            }
        }


class StopSpan:
    def __init__(self, request_id, span_id):
        print('StopSpan Command')
        self.request_id = request_id
        self.span_id = span_id

    def message(self):
        return {'StopSpan': {
            'request_id': self.request_id,
            'span_id': self.span_id,
        }}


class StartRequest:
    def __init__(self, request_id):
        print('StartRequest Command')
        self.request_id = request_id

    def message(self):
        return {'StartRequest': {
            'request_id': self.request_id,
        }}


class FinishRequest:
    def __init__(self, request_id):
        print('FinishRequest Command')
        self.request_id = request_id

    def message(self):
        return { 'FinishRequest': {
            'request_id': self.request_id,
        }}


class BatchedCommand:
    def __init__(self, commands):
        print('Batched Command')
        self.commands = commands

    def message(self):
        messages = map(lambda cmd: cmd.message(), self.commands)
        return {'BatchedCommand': messages}



