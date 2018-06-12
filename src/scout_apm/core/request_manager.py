from __future__ import absolute_import

import logging

from scout_apm.core.context import AgentContext
from scout_apm.core.thread_local import ThreadLocalSingleton

from .commands import BatchCommand

# Logging
logger = logging.getLogger(__name__)


class RequestManager(ThreadLocalSingleton):
    def __init__(self, *args, **kwargs):
        self.request_buffer = RequestBuffer()

    def add_request(self, request):
        if request.is_real_request():
            self.request_buffer.add_request(request)


class RequestBuffer(ThreadLocalSingleton):
    def __init__(self):
        self._requests = []

    # TODO: ensure there is a limit to the tracked requests in this buffer
    def add_request(self, request):
        self._requests.append(request)
        self.flush()

    def flush(self):
        logger.debug('Flushing RequestBuffer')
        for request in self._requests:
            logger.debug('Flushing Request Id: %s' % request.req_id)
            self.flush_request(request)
        del self._requests[:]

    def flush_request(self, request):
        batch_command = BatchCommand.from_tracked_request(request)
        if batch_command is not None:
            AgentContext.socket().send(batch_command)
