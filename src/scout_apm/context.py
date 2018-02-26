from __future__ import absolute_import

from .config.config import ScoutConfig
from .socket import CoreAgentSocket, RetryingCoreAgentSocket, ThreadedSocket
from .thread_local import ThreadLocalSingleton
from .commands import Register


class AgentContext(ThreadLocalSingleton):
    def __init__(self, *args, **kwargs):
        self.config = kwargs.get('config', ScoutConfig())
        self._socket = None

    def socket(self, *args, **kwargs):
        if self._socket is None:
            self._socket = ThreadedSocket(RetryingCoreAgentSocket(CoreAgentSocket(self.config.value('socket_path'))))
            self._socket.send(Register(app=self.config.value('name'),
                                       key=self.config.value('key')))
        return self._socket

    def __del__(self):
        if self._socket is not None:
            self._socket.stop_thread()
