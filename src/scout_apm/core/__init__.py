# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from kwargs_only import kwargs_only

from scout_apm.core import objtrace
from scout_apm.core.config import ScoutConfig
from scout_apm.core.context import AgentContext
from scout_apm.core.core_agent_manager import CoreAgentManager
from scout_apm.core.instrument_manager import InstrumentManager
from scout_apm.core.metadata import AppMetadata

logger = logging.getLogger(__name__)


@kwargs_only
def install(config=None):
    scout_config = ScoutConfig()
    if config is not None:
        scout_config.set(**config)
    context = AgentContext.build(config=scout_config)

    if os.name == "nt":
        logger.info(
            "APM Not Launching on PID: %s - Windows is not supported", os.getpid()
        )
        return False

    if not context.config.value("monitor"):
        logger.info(
            "APM Not Launching on PID: %s - Configuration 'monitor' is not true",
            os.getpid(),
        )
        return False

    InstrumentManager().install_all()

    objtrace.enable()

    logger.debug("APM Launching on PID: %s", os.getpid())
    launched = CoreAgentManager().launch()

    AppMetadata.report()
    if launched:
        AgentContext.socket().stop()

    return True
