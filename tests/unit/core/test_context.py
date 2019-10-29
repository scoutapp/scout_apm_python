# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.core.context import AgentContext
from scout_apm.core.socket import CoreAgentSocket


def test_agent_context_provides_socket():
    context = AgentContext.build()
    assert isinstance(context.socket(), CoreAgentSocket)
