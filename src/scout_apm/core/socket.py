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
from scout_apm.core.threading import SingletonThread

# Time unit - monkey-patched in tests to make them run faster
SECOND = 1

logger = logging.getLogger(__name__)


class CoreAgentSocketThread(SingletonThread):
    _instance_lock = threading.Lock()
    _stop_event = threading.Event()
    _command_queue = queue.Queue(maxsize=500)

    @classmethod
    def _on_stop(cls):
        super(CoreAgentSocketThread, cls)._on_stop()
        # Unblock _command_queue.get()
        cls._command_queue.put(None, False)

    @classmethod
    def send(cls, command):
        try:
            cls._command_queue.put(command, False)
        except queue.Full as exc:
            # TODO mark the command as not queued?
            logger.debug("CoreAgentSocketThread error on send: %r", exc, exc_info=exc)

        cls.ensure_started()

    def run(self):
        self.socket_path = scout_config.value("socket_path")
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        try:
            self._connect()
            self._register()
            while True:
                try:
                    body = self._command_queue.get(block=True, timeout=1 * SECOND)
                except queue.Empty:
                    body = None

                if body is not None:
                    result = self._send(body)
                    if result:
                        self._command_queue.task_done()
                    else:
                        # Something was wrong with the socket.
                        self._disconnect()
                        self._connect()
                        self._register()

                # Check for stop event after each read. This allows opening,
                # sending, and then immediately stopping. We do this for
                # the metadata event at application start time.
                if self._stop_event.is_set():
                    logger.debug("CoreAgentSocketThread stopping.")
                    break
        except Exception as exc:
            logger.debug("CoreAgentSocketThread exception: %r", exc, exc_info=exc)
        finally:
            self.socket.close()
            logger.debug("CoreAgentSocketThread stopped.")

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
                "CoreAgentSocketThread exception on length _send: "
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
                "CoreAgentSocketThread exception on data _send: "
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
            if len(raw_size) != 4:
                # Ignore invalid responses
                return None
            size = struct.unpack(">I", raw_size)[0]
            message = bytearray(0)

            while len(message) < size:
                recv = self.socket.recv(size)
                message += recv

            return message
        except OSError as exc:
            logger.debug(
                "CoreAgentSocketThread error on read response: %r", exc, exc_info=exc
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
                (
                    "CoreAgentSocketThread attempt %d, connecting to %s, "
                    + "PID: %s, Thread: %s"
                ),
                attempt,
                self.socket_path,
                os.getpid(),
                threading.current_thread(),
            )
            try:
                self.socket.connect(self.socket_path)
                self.socket.settimeout(3 * SECOND)
                logger.debug("CoreAgentSocketThread connected")
                return True
            except socket.error as exc:
                logger.debug(
                    "CoreAgentSocketThread connection error: %r", exc, exc_info=exc
                )
                # Return without waiting when reaching the maximum number of attempts.
                if attempt >= connect_attempts:
                    return False
                time.sleep(retry_wait_secs * SECOND)

    def _disconnect(self):
        logger.debug("CoreAgentSocketThread disconnecting from %s", self.socket_path)
        try:
            self.socket.close()
        except socket.error as exc:
            logger.debug(
                "CoreAgentSocketThread exception on disconnect: %r", exc, exc_info=exc
            )
        finally:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
