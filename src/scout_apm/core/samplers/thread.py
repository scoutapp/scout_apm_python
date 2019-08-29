# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import logging
import threading
import os

from scout_apm.core.commands import ApplicationEvent
from scout_apm.core.context import AgentContext
from scout_apm.core.samplers.cpu import Cpu
from scout_apm.core.samplers.memory import Memory

logger = logging.getLogger(__name__)


class SamplersThread(threading.Thread):
    _instance = None
    _instance_lock = threading.Lock()
    _stop_event = threading.Event()

    @classmethod
    def ensure_running(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(args, kwargs)
            return cls._instance

    @classmethod
    def ensure_stopped(cls):
        with cls._instance_lock:
            if cls._instance is None:
                # Nothing to stop
                return
            elif not cls._instance.is_alive():
                # Thread died
                cls._instance = None
                return

            # Signal stopping
            cls._stop_event.set()
            cls._instance.join()

            cls._instance = None
            cls._stop_event.clear()

    def __init__(self, *args, **kwargs):
        super(SamplersThread, self).__init__()

        # Set Thread options
        self.daemon = True

        # start() launches run() in another thread
        self.start()

    def __del__(self):
        self.stop()

    def run(self):
        logger.debug("Starting Samplers.")
        instances = [Cpu(), Memory()]

        while True:
            for instance in instances:
                event = ApplicationEvent()
                event.event_value = instance.run()
                event.event_type = (
                    instance.metric_type() + "/" + instance.metric_name()
                )
                event.timestamp = dt.datetime.utcnow()
                event.source = "Pid: " + str(os.getpid())

                if event.event_value is not None:
                    AgentContext.socket().send(event)

            should_stop = self._stop_event.wait(timeout=60)
            if should_stop:
                logger.debug("Shutting down samplers thread.")
                break
        self._stopped_event.set()
