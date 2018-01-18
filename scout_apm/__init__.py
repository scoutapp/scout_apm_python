from os import getpid
from threading import Thread
from time import sleep

from .django.signals import DjangoSignals
from .instruments.sql import SQLInstrument
from .instruments.template import TemplateInstrument
from .instruments.view import ViewInstrument

print('APM Launching on PID:', getpid())
SQLInstrument.install()
TemplateInstrument.install()
ViewInstrument.install()
DjangoSignals.install()

from .samplers.cpu import Cpu
from .samplers.memory import Memory

def samplers():
    print('Starting Samplers')
    instances = [Cpu(), Memory()]

    while True:
        for instance in instances:
            instance.run()
        sleep(10)

Thread(target=samplers).run()

