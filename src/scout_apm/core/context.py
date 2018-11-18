from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from scout_apm.core.config import ScoutConfig
from scout_apm.core.socket import CoreAgentSocket

logger = logging.getLogger(__name__)


class AgentContext(object):
    instance = None

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get("config", ScoutConfig())
        self.config.log()

    @classmethod
    def build(cls, *args, **kwargs):
        cls.instance = AgentContext(*args, **kwargs)
        return cls.instance

    @classmethod
    def socket(cls):
        return CoreAgentSocket.instance(scout_config=ScoutConfig())
