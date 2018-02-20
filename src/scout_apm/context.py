import sys

from .config.config import ScoutConfig
from .socket import CoreAgentSocket, RetryingCoreAgentSocket, ThreadedSocket


class AgentContext:
    def __init__(self, conf, socket):
        self.config = conf
        self.socket = socket


# this is a pointer to the module object instance itself.
this = sys.modules[__name__]

# Initialize the Context object for the rest of the system to use
conf = ScoutConfig()
socket = ThreadedSocket(RetryingCoreAgentSocket(CoreAgentSocket(conf.value('socket_path'))))
this.agent_context = AgentContext(conf, socket)
