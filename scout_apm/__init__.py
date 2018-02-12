# Python Modules
import logging
from os import getpid

# APM Modules
from scout_apm.django.signals import DjangoSignals
from scout_apm.instruments.sql import SQLInstrument
from scout_apm.instruments.template import TemplateInstrument
from scout_apm.instruments.view import ViewInstrument
from scout_apm.samplers.samplers import Samplers
from scout_apm.core_agent_manager import CoreAgentManager

# Logging
logger = logging.getLogger(__name__)


def install():
    logger.info('APM Launching on PID:', getpid())
    SQLInstrument.install()
    TemplateInstrument.install()
    ViewInstrument.install()
    DjangoSignals.install()

    CoreAgentManager().launch()

# XXX: This blocks manage.py's web server, since it starts a permanent thread
# Look into how to run after forking in django. Across distinct kinds of web
# servers?
#
# Samplers.install()
