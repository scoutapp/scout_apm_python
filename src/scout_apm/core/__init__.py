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
except ImportError:
    objtrace = None

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

    if objtrace is not None:
        objtrace.enable()

    logger.debug("APM Launching on PID: %s", getpid())
    launched = CoreAgentManager().launch()

    AppMetadata.report()
    if launched:
        AgentContext.socket().stop()

    return True
