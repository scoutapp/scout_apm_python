# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from scout_apm.compat import kwargs_only
from scout_apm.core import objtrace
from scout_apm.core.config import scout_config
from scout_apm.core.core_agent_manager import CoreAgentManager
from scout_apm.core.instrument_manager import InstrumentManager
from scout_apm.core.metadata import report_app_metadata
from scout_apm.core.socket import CoreAgentSocket

logger = logging.getLogger(__name__)


@kwargs_only
def install(config=None):
    if config is not None:
        scout_config.set(**config)
    scout_config.log()

    if os.name == "nt":
        logger.info(
            "APM Not Launching on PID: %s - Windows is not supported", os.getpid()
        )
        return False

    if not scout_config.value("monitor"):
        logger.info(
            "APM Not Launching on PID: %s - Configuration 'monitor' is not true",
            os.getpid(),
        )
        return False

    InstrumentManager().install_all()

    objtrace.enable()

    logger.debug("APM Launching on PID: %s", os.getpid())
    launched = CoreAgentManager().launch()

    report_app_metadata()
    if launched:
        # Stop the thread to avoid running threads pre-fork
        CoreAgentSocket.instance().stop()

    return True
