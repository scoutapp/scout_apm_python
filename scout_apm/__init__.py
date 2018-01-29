from os import getpid

from .django.signals import DjangoSignals
from .instruments.sql import SQLInstrument
from .instruments.template import TemplateInstrument
from .instruments.view import ViewInstrument
from .samplers.samplers import Samplers

print('APM Launching on PID:', getpid())

SQLInstrument.install()
TemplateInstrument.install()
ViewInstrument.install()
DjangoSignals.install()

# XXX: This blocks manage.py's web server, since it starts a permanent thread
# Look into how to run after forking in django. Across distinct kinds of web
# servers?
#
# Samplers.install()
