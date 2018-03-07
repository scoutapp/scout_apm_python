from __future__ import absolute_import

from .config.config import ScoutConfig
from .socket import CoreAgentSocket
from .thread_local import ThreadLocalSingleton

class AgentContext(ThreadLocalSingleton):
    def __init__(self, *args, **kwargs):
        self.config = kwargs.get('config', ScoutConfig())
        self._socket = None

    def socket(self, *args, **kwargs):
        if self._socket is None:
            self._socket = CoreAgentSocket(self.config.value('socket_path'))
        return self._socket

    def __del__(self):
        if self._socket is not None:
            self._socket.stop()
