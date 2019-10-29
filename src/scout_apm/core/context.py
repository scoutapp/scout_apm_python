# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.core.config import scout_config
from scout_apm.core.socket import CoreAgentSocket


class AgentContext(object):
    instance = None

    def __init__(self):
        scout_config.log()

    @classmethod
    def build(cls, *args, **kwargs):
        cls.instance = AgentContext(*args, **kwargs)
        return cls.instance

    @classmethod
    def socket(cls):
        return CoreAgentSocket.instance()
