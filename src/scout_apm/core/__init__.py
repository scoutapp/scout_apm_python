from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from os import getpid

from scout_apm.core.config import ScoutConfig
from scout_apm.core.context import AgentContext
from scout_apm.core.core_agent_manager import CoreAgentManager
from scout_apm.core.instrument_manager import InstrumentManager
from scout_apm.core.metadata import AppMetadata

try:
    from scout_apm.core import objtrace

    HAS_OBJTRACE = True
except ImportError:
    HAS_OBJTRACE = False

logger = logging.getLogger(__name__)


def install(*args, **kwargs):
    if "config" in kwargs:
        ScoutConfig().set(**kwargs["config"])
    context = AgentContext.build(config=ScoutConfig())

    if not context.config.value("monitor"):
        logger.info(
            "APM Not Launching on PID: %s - Configuration 'monitor' is not true",
            getpid(),
        )
        return False

    InstrumentManager().install_all()

    if HAS_OBJTRACE:
        objtrace.enable()

    logger.debug("APM Launching on PID: %s", getpid())
    CoreAgentManager().launch()

    AppMetadata.report()
    AgentContext.socket().stop()
    return True
