from os import getpid;

print("APM Launching on PID: ", getpid())
from .instruments.sql import SQLInstrument;
from .instruments.template import TemplateInstrument;
from .instruments.view import ViewInstrument;
SQLInstrument.init()
TemplateInstrument.init()
ViewInstrument.init()



