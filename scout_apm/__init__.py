from os import getpid

from .django.signals import DjangoSignals
from .instruments.sql import SQLInstrument
from .instruments.template import TemplateInstrument
from .instruments.view import ViewInstrument

print('APM Launching on PID:', getpid())
SQLInstrument.install()
TemplateInstrument.install()
ViewInstrument.install()
DjangoSignals.install()


