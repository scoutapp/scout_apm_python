from os import getpid
from threading import Thread
import json
import datetime
from time import sleep

from .cpu import Cpu
from .memory import Memory
from scout_apm.tracked_request import CoreAgentSocket


class Samplers():
    def install():
        Thread(target=Samplers.samplers).run()

    @staticmethod
    def samplers():
        print('Starting Samplers')

        socket = CoreAgentSocket()
        instances = [Cpu(), Memory()]

        while True:
            for instance in instances:
                event_value = instance.run()
                event_type = instance.metric_type() + "/" + instance.metric_name()
                moment = datetime.datetime.utcnow().isoformat() + 'Z'
                source = "Pid: " + str(getpid())

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



