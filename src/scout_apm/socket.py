import json
import logging
import socket
import struct
import time

# Make this a thread local - so each thread has its own socket. Can't be global
# though w/o otherwise locking it.

# Logging
logger = logging.getLogger(__name__)


class CoreAgentSocket:
    def __init__(self, socket_path='/tmp/scout_core_agent'):
        self.socket_path = socket_path

    def open(self):
        logger.info('CoreAgentSocket connecting to', self.socket_path)
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(self.socket_path)
            logger.info('CoreAgentSocket Opened Successfully')
            return True
        except ConnectionRefusedError:
            logger.info('Connection refused error')
            return None

    def send(self, command):
        msg = command.message()
        data = json.dumps(msg)
        self.socket.sendall(self.message_length(data))
        self.socket.sendall(data.encode())
        return self.read_response()

    def message_length(self, body):
        length = len(body)
        return length.to_bytes(4, 'big')

    def read_response(self):
        raw_size = self.socket.recv(4)
        size = struct.unpack('<I', raw_size)[0]
        message = self.socket.recv(size)
        return message

    def close(self):
        self.socket.close()


class RetryingCoreAgentSocket:
    """
    Wraps a CoreAgentSocket instance, and adds retry & error handling logic.
    """

    def __init__(self, core_agent_socket):
        self.socket = core_agent_socket

    def send(self, body):
        try:
            self.socket.send(body)
        except ConnectionRefusedError as err:
            logger.info('ConnectionRefusedError,', err)
            self.open()
            self.send(self, body)
        except OSError as err:
            logger.info('OSError,', err)

    def open(self):
        logger.info('RetryingCoreAgentSocket open')
        delay = 1
        while True:
            if self.socket.open() is None:
                logger.info('RetryingCoreAgentSocket, sleeping for', delay)
                time.sleep(delay)
                delay += 1
            else:
                return True

    def close(self):
        self.socket.close()
