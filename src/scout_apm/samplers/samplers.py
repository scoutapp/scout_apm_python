import datetime
import json
import logging
from os import getpid
from threading import Thread
from time import sleep

from scout_apm.context import AgentContext
from scout_apm.commands import ApplicationEvent

from .cpu import Cpu
from .memory import Memory

# Logging
logger = logging.getLogger(__name__)


class Samplers():
    def install():
        th = Thread(target=Samplers.samplers)
        th.daemon = True
        th.run()

    @staticmethod
    def samplers():
        logger.info('Starting Samplers')

        socket = AgentContext.instance().socket()
        instances = [Cpu(), Memory()]

        while True:
            for instance in instances:
                event = ApplicationEvent()
                event.event_value = instance.run()
                event.event_type = instance.metric_type() + '/' + instance.metric_name()
                event.moment = datetime.datetime.utcnow().isoformat() + 'Z'
                event.source = 'Pid: ' + str(getpid())

                if event.event_value is not None:
                    socket.send(event)
            sleep(60)
