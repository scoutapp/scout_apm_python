from __future__ import absolute_import

import json
import logging
import socket
import struct
import time
import threading

try:
    # Python 3.x
    import queue
except ImportError:
    # Python 2.x
    import Queue as queue

from scout_apm.config.config import ScoutConfig
from scout_apm.commands import Register

# Logging
logger = logging.getLogger(__name__)


class CoreAgentSocket(threading.Thread):
    def __init__(self, *args, **kwargs):
        # Call threading.Thread.__init__()
        super(CoreAgentSocket, self).__init__()
        self.config = kwargs.get('scout_config', ScoutConfig())
        # Socket related
        self.socket_path = self.config.value('socket_path')
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Threading related
        self._stop_event = threading.Event()
        self.queue = queue.Queue()
        self.daemon = True
        self.start()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        self._connect()
        self._register()

        while True:
            if self.stopped():
                logger.debug("CoreAgentSocket thread exiting.")
                break

            try:
                body = self.queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            if body is not None:
                result = self._send(body)
                if result is True:
                    self.queue.task_done()
                elif result is False:
                    # Something was wrong with the command.
                    self.queue.task_done()
                else:
                    # Something was wrong with the socket.
                    self._disconnect()
                    self._connect()
                    self._register()

    def send(self, command):
        try:
            self.queue.put(command)
        except Exception as e:
            # TODO mark the command as not queued?
            logger.debug('CoreAgentSocket error on send: %s' % repr(e))

    def _send(self, command, async=True):
        try:
            msg = command.message()
        except Exception as e:
            log.debug('Exception when getting command message: %s' % repr(e))
            return False

        try:
            data = json.dumps(msg)
        except Exception as e:
            log.debug('Exception when serializing command message: %s' % repr(e))
            return False

        try:
            self.socket.sendall(self._message_length(data))
            self.socket.sendall(data.encode())
        except Exception as e:
            logger.debug("CoreAgentSocket exception on _send: %s" % repr(e))
            return None

        if async is True:
            return True
        else:
            # TODO read respnse back in to command
            self._read_response()
            return True

    def _message_length(self, body):
        length = len(body)
        return length.to_bytes(4, 'big')

    def _read_response(self):
        try:
            raw_size = self.socket.recv(4)
            size = struct.unpack('<I', raw_size)[0]
            message = self.socket.recv(size)
            return message
        except Exception as e:
            logger.debug('CoreAgentSocket error on read response: %s' % repr(e))
            return None

    def _register(self):
        self._send(Register(app=self.config.value('name'),
                            key=self.config.value('key')))

    def _connect(self, connect_attempts=5, retry_wait_secs=1):
        for attempt in range(1, connect_attempts):
            logger.debug('CoreAgentSocket attempt %d, connecting to %s', attempt, self.socket_path)
            try:
                self.socket.connect(self.socket_path)
                self.socket.settimeout(0.5)
                logger.debug('CoreAgentSocket is connected')
                return True
            except Exception as e:
                logger.debug('CoreAgentSocket connection error: %s', repr(e))
                if attempt >= connect_attempts:
                    return False
                time.sleep(retry_wait_secs)
                continue

    def _disconnect(self):
        logger.debug('CoreAgentSocket disconnecting from %s', self.socket_path)
        try:
            self.socket.close()
        except Exception as e:
            logger.debug('CoreAgentSocket exception on disconnect: %s' % repr(e))
        finally:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
