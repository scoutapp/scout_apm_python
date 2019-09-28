# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import logging
import threading
from os import getpid
from time import sleep

from scout_apm.core.commands import ApplicationEvent
from scout_apm.core.context import AgentContext
from scout_apm.core.samplers.cpu import Cpu
from scout_apm.core.samplers.memory import Memory

logger = logging.getLogger(__name__)


class Samplers(object):
    _thread_lock = threading.Semaphore()

    @classmethod
    def ensure_running(cls):
        if cls._thread_lock.acquire(False):
            th = threading.Thread(target=Samplers.run_samplers)
            th.daemon = True
            th.start()
            cls._thread_lock.release()

    @classmethod
    def run_samplers(cls):
        logger.debug("Starting Samplers. Acquiring samplers lock.")
        try:
            if cls._thread_lock.acquire(True):
                logger.debug("Acquired samplers lock.")
                instances = [Cpu(), Memory()]

                while True:
                    for instance in instances:
                        event_value = instance.run()
                        if event_value is not None:
                            event_type = (
                                instance.metric_type() + "/" + instance.metric_name()
                            )
                            event = ApplicationEvent(
                                event_value=event_value,
                                event_type=event_type,
                                timestamp=dt.datetime.utcnow(),
                                source="Pid: " + str(getpid()),
                            )
                            AgentContext.socket().send(event)
                    sleep(60)
        finally:
            logger.debug("Shutting down samplers thread.")
            cls._thread_lock.release()
