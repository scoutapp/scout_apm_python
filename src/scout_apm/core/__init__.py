# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sys
from os import getpid

from scout_apm.core import objtrace
from scout_apm.core.config import ScoutConfig
from scout_apm.core.context import AgentContext
from scout_apm.core.core_agent_manager import CoreAgentManager
from scout_apm.core.instrument_manager import InstrumentManager
from scout_apm.core.metadata import AppMetadata

logger = logging.getLogger(__name__)


def install(*args, **kwargs):
    if "config" in kwargs:
        ScoutConfig().set(**kwargs["config"])
    context = AgentContext.build(config=ScoutConfig())

    if sys.platform == "win32":
        logger.info("APM Not Launching on PID: %s - Windows is not supported", getpid())
        return False

    if not context.config.value("monitor"):
        logger.info(
            "APM Not Launching on PID: %s - Configuration 'monitor' is not true",
            getpid(),
        )
        return False

    InstrumentManager().install_all()

    objtrace.enable()

    logger.debug("APM Launching on PID: %s", getpid())
    launched = CoreAgentManager().launch()

    AppMetadata.report()
    if launched:
        AgentContext.socket().stop()

    return True
