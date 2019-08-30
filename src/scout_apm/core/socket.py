# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging
import os
import socket
import struct
import threading
import time

from scout_apm.compat import queue
from scout_apm.core.commands import Register
from scout_apm.core.config import scout_config

SECOND = 1  # time unit - monkey-patched in tests to make them run faster

logger = logging.getLogger(__name__)


class CoreAgentSocket(threading.Thread):
    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls):
        with cls._instance_lock:
            # No instance exists yet.
            if cls._instance is None:
                cls._instance = cls()
                return cls._instance

            # An instance exists but is no longer running.
            if not cls._instance.running():
                cls._instance = cls()
                return cls._instance

            # An instance exists and is running (or in the process of
            # starting or in the process of stopping). In any case,
            # return this instance.
            return cls._instance

    def __init__(self, *args, **kwargs):
        super(CoreAgentSocket, self).__init__()
        # Socket related
        self.socket_path = scout_config.value("socket_path")
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
            self.command_queue.put(None, False)  # unblock self.command_queue.get
            stopped = self._stopped_event.wait(2 * SECOND)
            if stopped:
                return True
            else:
                logger.debug("CoreAgentSocket Failed to stop thread within timeout!")
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
                    body = self.command_queue.get(block=True, timeout=1 * SECOND)
                except queue.Empty:
                    body = None

                if body is not None:
                    result = self._send(body)
                    if result:
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
        except Exception as exc:
            logger.debug("CoreAgentSocket thread exception: %r", exc, exc_info=exc)
        finally:
            self._started_event.clear()
            self._stop_event.clear()
            self._stopped_event.set()
            logger.debug("CoreAgentSocket thread stopped.")

    def send(self, command):
        try:
            self.command_queue.put(command, False)
        except queue.Full as exc:
            # TODO mark the command as not queued?
            logger.debug("CoreAgentSocket error on send: %r", exc, exc_info=exc)

    def _send(self, command):
        msg = command.message()

        try:
            data = json.dumps(msg)
        except (ValueError, TypeError) as exc:
            logger.debug(
                "Exception when serializing command message: %r", exc, exc_info=exc
            )
            return False

        try:
            self.socket.sendall(self._message_length(data))
        except OSError as exc:
            logger.debug(
                "CoreAgentSocket exception on length _send: "
                "%r on PID: %s on thread: %s",
                exc,
                os.getpid(),
                threading.current_thread(),
                exc_info=exc,
            )
            return None

        try:
            self.socket.sendall(data.encode())
        except OSError as exc:
            logger.debug(
                "CoreAgentSocket exception on data _send: "
                "%r on PID: %s on thread: %s",
                exc,
                os.getpid(),
                threading.current_thread(),
                exc_info=exc,
            )
            return None

        # TODO do something with the response sent back in reply to command
        self._read_response()

        return True

    def _message_length(self, body):
        length = len(body)
        return struct.pack(">I", length)

    def _read_response(self):
        try:
            raw_size = self.socket.recv(4)
            size = struct.unpack(">I", raw_size)[0]
            message = bytearray(0)

            while len(message) < size:
                recv = self.socket.recv(size)
                message += recv

            return message
        except OSError as exc:
            logger.debug(
                "CoreAgentSocket error on read response: %r", exc, exc_info=exc
            )
            return None

    def _register(self):
        self._send(
            Register(
                app=scout_config.value("name"),
                key=scout_config.value("key"),
                hostname=scout_config.value("hostname"),
            )
        )

    def _connect(self, connect_attempts=5, retry_wait_secs=1):
        for attempt in range(1, connect_attempts + 1):
            logger.debug(
                "CoreAgentSocket attempt %d, connecting to %s, PID: %s, Thread: %s",
                attempt,
                self.socket_path,
                os.getpid(),
                threading.current_thread(),
            )
            try:
                self.socket.connect(self.socket_path)
                self.socket.settimeout(3 * SECOND)
                logger.debug("CoreAgentSocket is connected")
                return True
            except socket.error as exc:
                logger.debug("CoreAgentSocket connection error: %r", exc, exc_info=exc)
                # Return without waiting when reaching the maximum number of attempts.
                if attempt >= connect_attempts:
                    return False
                time.sleep(retry_wait_secs * SECOND)

    def _disconnect(self):
        logger.debug("CoreAgentSocket disconnecting from %s", self.socket_path)
        try:
            self.socket.close()
        except socket.error as exc:
            logger.debug(
                "CoreAgentSocket exception on disconnect: %r", exc, exc_info=exc
            )
        finally:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
