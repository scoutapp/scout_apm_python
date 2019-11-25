# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import logging
import os
import threading

from scout_apm.core.commands import ApplicationEvent
from scout_apm.core.samplers.cpu import Cpu
from scout_apm.core.samplers.memory import Memory
from scout_apm.core.socket import CoreAgentSocket

logger = logging.getLogger(__name__)


class SamplersThread(threading.Thread):
    _instance = None
    _instance_lock = threading.Lock()
    _stop_event = threading.Event()

    @classmethod
    def ensure_started(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._instance.start()

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
        super(SamplersThread, self).__init__(*args, **kwargs)
        self.daemon = True

    def run(self):
        logger.debug("Starting Samplers.")
        instances = [Cpu(), Memory()]

        while True:
            for instance in instances:
                event_value = instance.run()
                if event_value is not None:
                    event_type = instance.metric_type + "/" + instance.metric_name
                    event = ApplicationEvent(
                        event_value=event_value,
                        event_type=event_type,
                        timestamp=dt.datetime.utcnow(),
                        source="Pid: " + str(os.getpid()),
                    )
                    CoreAgentSocket.instance().send(event)

            should_stop = self._stop_event.wait(timeout=60)
            if should_stop:
                logger.debug("Stopping Samplers.")
                break
