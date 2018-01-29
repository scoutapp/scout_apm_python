import socket
import time
import json
import struct

# Make this a thread local - so each thread has its own socket. Can't be global
# though w/o otherwise locking it.


class CoreAgentSocket:
    def __init__(self, server_address='/tmp/scout_core_agent'):
        self.server_address = server_address

    def open(self):
        print('CoreAgentSocket connecting to', self.server_address)
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(self.server_address)
            print('CoreAgentSocket Opened Successfully')
            return True
        except ConnectionRefusedError:
            print('Connection refused error')
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
        print('Received response:', message)
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
            print('ConnectionRefusedError,', err)
            self.open()
            self.send(self, body)
        except OSError as err:
            print('OSError,', err)

    def open(self):
        print('RetryingCoreAgentSocket open')
        delay = 1
        while True:
            if self.socket.open() is None:
                print('RetryingCoreAgentSocket, sleeping for', delay)
                time.sleep(delay)
                delay += 1
            else:
                return True

    def close(self):
        self.socket.close()


class BatchingCoreAgentSocket:
    """
    Wraps a socket with batching logic.

    It stores messages until a `flush` command is sent. Then it wraps the
    messages in a "CommandBatch" type, and sends the entire set.
    """
