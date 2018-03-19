from __future__ import absolute_import
import logging

from .config.config import ScoutConfig
from .socket import CoreAgentSocket
from .thread_local import ThreadLocalSingleton

# Logging
logger = logging.getLogger(__name__)


class AgentContext(ThreadLocalSingleton):
    def __init__(self, *args, **kwargs):
        self.config = kwargs.get('config', ScoutConfig())

    @classmethod
    def socket(cls):
        return CoreAgentSocket.instance(scout_config=ScoutConfig())
