from datetime import datetime
import logging
import threading
from os import getpid
from time import sleep

from scout_apm.context import AgentContext
from scout_apm.commands import ApplicationEvent

from scout_apm.samplers.cpu import Cpu
from scout_apm.samplers.memory import Memory

# Logging
logger = logging.getLogger(__name__)


class Samplers():
    thread_lock = threading.Semaphore()

    @classmethod
    def ensure_running(cls):
        try:
            if cls.thread_lock.acquire(False) is True:
                th = threading.Thread(target=Samplers.run_samplers)
                th.daemon = True
                th.start()
        finally:
            cls.thread_lock.release()

    @classmethod
    def run_samplers(cls):
        logger.info('Starting Samplers. Acquiring samplers lock.')
        try:
            if cls.thread_lock.acquire(True) is True:
                logger.info('Acquired samplers lock.')
                socket = AgentContext.instance().socket()
                instances = [Cpu(), Memory()]

                while True:
                    for instance in instances:
                        event = ApplicationEvent()
                        event.event_value = instance.run()
                        event.event_type = instance.metric_type() + '/' + instance.metric_name()
                        event.timestamp = datetime.utcnow()
                        event.source = 'Pid: ' + str(getpid())

                        if event.event_value is not None:
                            socket.send(event)
                    sleep(60)
        finally:
            cls.thread_lock.release()
