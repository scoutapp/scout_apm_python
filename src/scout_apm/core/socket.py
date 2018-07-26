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

from scout_apm.core.config import ScoutConfig
from scout_apm.core.commands import Register

# Logging
logger = logging.getLogger(__name__)


class CoreAgentSocket(threading.Thread):
    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls, *args, **kwargs):
        with cls._instance_lock:
            # No instance exists yet.
            if cls._instance is None:
                cls._instance = cls(args, kwargs)
                return cls._instance

            # An instance exists but is no longer running.
            if cls._instance.running() is False:
                cls._instance = cls(args, kwargs)
                return cls._instance

            # An instance exists and is running (or in the process of
            # starting or in the process of stopping). In any case,
            # return this instance.
            return cls._instance

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.config = kwargs.get('scout_config', ScoutConfig())

        # Socket related
        self.socket_path = self.config.value('socket_path')
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # Threading control related
        self._started_event = threading.Event()
        self._stop_event = threading.Event()
        self._stopped_event = threading.Event()

        # Command queues
        self.command_queue = queue.Queue(maxsize=500)

        # Set Thread options
        self.daemon = True

        # Set the started event here to avoid races in the class instance()
        # method. If there is an exception in the socket thread then it will
        # clear this event on exit.
        self._started_event.set()

        # Now call start() which eventually launches run() in another thread.
        self.start()

    def __del__(self):
        self.stop()

    def running(self):
        return self._started_event.is_set()

    def stop(self):
        if self._started_event.is_set():
            self._stop_event.set()
            self._stopped_event.wait(2)
            if self._stopped_event.is_set():
                return True
            else:
                logger.debug('CoreAgentSocket Failed to stop thread within timeout!')
                return False
        else:
            return True

    def run(self):
        """
        Called by the threading system
        """

        try:
            self._connect()
            self._register()
            while True:
                try:
                    body = self.command_queue.get(block=True, timeout=1)
                except queue.Empty:
                    continue

                if body is not None:
                    result = self._send(body)
                    if result is True:
                        self.command_queue.task_done()
                    else:
                        # Something was wrong with the socket.
                        self._disconnect()
                        self._connect()
                        self._register()

                # Check for stop event after a read from the queue. This is to
                # allow you to open a socket, immediately send to it, and then
                # stop it. We do this in the Metadata send at application start
                # time
                if self._stop_event.is_set():
                    logger.debug("CoreAgentSocket thread stopping.")
                    break
        except:
            logger.debug("CoreAgentSocket thread exception")
        finally:
            self._started_event.clear()
            self._stop_event.clear()
            self._stopped_event.set()
            logger.debug("CoreAgentSocket thread stopped.")

    def send(self, command):
        try:
            self.command_queue.put(command, False)
        except queue.Full as e:
            # TODO mark the command as not queued?
            logger.debug('CoreAgentSocket error on send: %s' % repr(e))

    def _send(self, command, do_async=True):
        msg = command.message()

        try:
            data = json.dumps(msg)
        except (ValueError, TypeError) as e:
            logger.debug('Exception when serializing command message: %s' % repr(e))
            return False

        try:
            self.socket.sendall(self._message_length(data))
            self.socket.sendall(data.encode())
        except (OSError) as e:
            logger.debug("CoreAgentSocket exception on _send: %s" % repr(e))
            return None

        if do_async is True:
            return True
        else:
            # TODO read respnse back in to command
            self._read_response()
            return True

    def _message_length(self, body):
        length = len(body)
        return struct.pack('>I', length)

    def _read_response(self):
        try:
            raw_size = self.socket.recv(4)
            size = struct.unpack('>I', raw_size)[0]
            message = self.socket.recv(size)
            return message
        except (OSError) as e:
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
            except (OSError) as e:
                logger.debug('CoreAgentSocket connection error: %s', repr(e))
                if attempt >= connect_attempts:
                    return False
                time.sleep(retry_wait_secs)
                continue

    def _disconnect(self):
        logger.debug('CoreAgentSocket disconnecting from %s', self.socket_path)
        try:
            self.socket.close()
        except (OSError) as e:
            logger.debug('CoreAgentSocket exception on disconnect: %s' % repr(e))
        finally:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
