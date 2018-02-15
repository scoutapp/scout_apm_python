import datetime
import json
import logging
from os import getpid
from threading import Thread
from time import sleep

from scout_apm.context import agent_context

from .cpu import Cpu
from .memory import Memory

# Logging
logger = logging.getLogger(__name__)

# Logging
logger = logging.getLogger(__name__)


class Samplers():
    def install():
        Thread(target=Samplers.samplers).run()

    @staticmethod
    def samplers():
        logger.info('Starting Samplers')

        socket = agent_context.socket
        instances = [Cpu(), Memory()]

        while True:
            for instance in instances:
                event_value = instance.run()
                event_type = instance.metric_type() + '/' + instance.metric_name()
                moment = datetime.datetime.utcnow().isoformat() + 'Z'
                source = 'Pid: ' + str(getpid())

                if event_value is not None:
                    socket.send(json.dumps({
                        'ApplicationEvent': {
                            'event_type':  event_type,
                            'event_value': event_value,
                            'moment': moment,
                            'source': source,
                        }
                    }))
            sleep(10)
