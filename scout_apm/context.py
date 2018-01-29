import sys

from .config.config import ScoutConfig
from .socket import CoreAgentSocket, RetryingCoreAgentSocket


class AgentContext:
    def __init__(self, conf, socket):
        self.conf = conf
        self.socket = socket


# this is a pointer to the module object instance itself.
this = sys.modules[__name__]

# Initialize the Context object for the rest of the system to use
conf = ScoutConfig()
socket = RetryingCoreAgentSocket(CoreAgentSocket())
this.agent_context = AgentContext(conf, socket)
