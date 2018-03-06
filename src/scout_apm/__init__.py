from __future__ import absolute_import

# Python Modules
import logging
from os import getpid
import time

from scout_apm.core_agent_manager import CoreAgentManager
from scout_apm.metadata import AppMetadata

logger = logging.getLogger(__name__)


def install():
    logger.info('APM Launching on PID: %s', getpid())
    CoreAgentManager().launch()
    time.sleep(2)
    AppMetadata.report()
