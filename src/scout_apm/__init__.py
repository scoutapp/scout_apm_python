# Python Modules
import logging
from os import getpid

from scout_apm.core_agent_manager import CoreAgentManager
logger = logging.getLogger(__name__)


def install():
    logger.info('APM Launching on PID: %s', getpid())
    CoreAgentManager().launch()

# XXX: This blocks manage.py's web server, since it starts a permanent thread
# Look into how to run after forking in django. Across distinct kinds of web
# servers?
#
# from scout_apm.samplers.samplers import Samplers
# Samplers.install()
