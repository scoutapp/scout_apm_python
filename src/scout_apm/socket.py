import json
import logging
import socket
import struct
import threading
import queue
import time

# Make this a thread local - so each thread has its own socket. Can't be global
# though w/o otherwise locking it.

# Logging
logger = logging.getLogger(__name__)


class CoreAgentSocket:
    def __init__(self, socket_path='/tmp/scout_core_agent'):
        self.socket_path = socket_path

    def open(self):
        logger.info('CoreAgentSocket connecting to %s', self.socket_path)
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

    def __init__(self, underlying):
        self.underlying = underlying

    def send(self, body):
        try:
            self.underlying.send(body)
        except ConnectionRefusedError as err:
            logger.info('ConnectionRefusedError %s', err)
            self.open()
            self.send(self, body)
        except OSError as err:
            logger.info('OSError,', err)

    def open(self):
        logger.info('RetryingCoreAgentSocket open')
        delay = 1
        while True:
            if self.underlying.open() is None:
                logger.info('RetryingCoreAgentSocket, sleeping for %d', delay)
                time.sleep(delay)
                delay += 1
            else:
                return True

    def close(self):
        self.underlying.close()


# TODO: Look into capping the size of the internal queue, to prevent a dead
# thread from having a never-ending queue size.
class ThreadedSocket:
    """
    Wraps another Socket, pushing all writes into a background thread.
    The thread is entirely managed by this class.
    """

    def __init__(self, underlying):
        self.underlying = underlying
        self.queue = queue.Queue()
        self.worker = None

    def send(self, body):
        self.ensure_thread()
        self.queue.put(body)

    def open(self):
        logger.info('Socket Thread: Open')
        self.ensure_thread()
        self.underlying.open()

    def close(self):
        logger.info('Socket Thread: Closing')
        self.stop_thread()
        self.underlying.close()

    def ensure_thread(self):
        if self.thread_running() is False:
            self.start_thread()

    def thread_running(self):
        if self.worker is not None:
            self.worker.is_alive()
        else:
            return False

    def start_thread(self):
        logger.info('Socket Thread: Starting Thread')
        self.worker = ThreadedSocketWorker(self.queue, self.underlying)
        self.worker.daemon = True
        self.worker.start()

    def stop_thread(self):
        if self.thread_running():
            logger.info('Socket Thread: Stopping Thread')
            self.worker.stop()
            self.worker.join()
        else:
            logger.info('Socket Thread: Stopping, Not running, can\'t stop')


class ThreadedSocketWorker(threading.Thread):
    def __init__(self, queue, underlying):
        super(ThreadedSocketWorker, self).__init__()
        self._stop_event = threading.Event()
        self.underlying = underlying
        self.queue = queue

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        while True:
            if self.stopped():
                break

            try:
                body = self.queue.get(block=True, timeout=1)
                if body is None:
                    break
                self.underlying.send(body)
                self.queue.task_done()
            except queue.Empty:
                logger.info('Got Empty exception')
