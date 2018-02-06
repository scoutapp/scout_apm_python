from os import getpid

from scout_apm.django.signals import DjangoSignals
from scout_apm.instruments.sql import SQLInstrument
from scout_apm.instruments.template import TemplateInstrument
from scout_apm.instruments.view import ViewInstrument
from scout_apm.samplers.samplers import Samplers
from scout_apm.core_agent_manager import CoreAgentManager

def install():
    print('APM Launching on PID:', getpid())
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
