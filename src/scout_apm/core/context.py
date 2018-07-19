from __future__ import absolute_import
import logging

from .config import ScoutConfig
from .socket import CoreAgentSocket

# Logging
logger = logging.getLogger(__name__)


class AgentContext():
    instance = None

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get('config', ScoutConfig())
        self.config.log()

    @classmethod
    def build(cls, *args, **kwargs):
        cls.instance = AgentContext(*args, **kwargs)
        return cls.instance

    @classmethod
    def socket(cls):
        return CoreAgentSocket.instance(scout_config=ScoutConfig())
