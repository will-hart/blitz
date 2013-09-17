__author__ = 'Will Hart'

import logging
import threading
import Queue
import zmq

from blitz.io.client_states import *
from blitz.io.server_states import *
import blitz.io.signals as sigs


class TcpCommunicationException(Exception):
    pass


class TcpBase(object):
    REQUEST_TIMEOUT = 2000
    REQUEST_RETRIES = 3
    SERVER_ENDPOINT = "tcp://%s:%s"
    MAX_RESPONSE_LENGTH = 1024

    logger = logging.getLogger(__name__)

    def __init__(self, host="localhost", port=None):
        self.__host = host
        self.__port = port
        self.send_queue = Queue.Queue()
        self.waiting = False
        self.__poller = zmq.Poller()
        self.__stop_event = threading.Event()
        self.__thread = None
        self.__state_machine = None

    def create_client(self, autorun=True):
        self.__context = zmq.Context(1)
        self.__socket = self.__context.socket(zmq.REQ)
        self.__socket.connect(self.SERVER_ENDPOINT % (self.__host, self.__port))
        self.__state_machine = TcpStateMachine(self, self.__stop_event, ClientInitState)

        if autorun:
            self.__run_thread(self.run_client)

    def create_server(self):
        self.__context = zmq.Context(1)
        self.__socket = self.__context.socket(zmq.REP)
        self.__socket.bind(self.SERVER_ENDPOINT % ("*", self.__port))
        self.__state_machine = TcpStateMachine(self, self.__stop_event, ServerIdleState)
        self.__run_thread(self.run_server)

    def __run_thread(self, thread_target):
        self.__poller.register(self.__socket, zmq.POLLIN)
        self.__thread = threading.Thread(target=thread_target, args=[self.__stop_event])
        self.__thread.daemon = True
        self.__thread.start()

    def is_alive(self):
        return not self.__stop_event.is_set()

    def is_logging(self):
        return self.__state_machine is not None and self.__state_machine.is_logging()

    def stop(self):
        self.__stop_event.set()
        if self.__thread is not None:
            self.__thread.join()
        if self.__state_machine is not None:
            self.__state_machine.join()
        self.__stop_event.clear()

    def _do_send(self, message):
        self.send_queue.put(message)

    def send(self, message):
        self.__state_machine.queue_send(message)

    def receive_message(self, message):
        self.__state_machine.queue_receive(message)

    def run_server(self, stop_event):
        self.logger.debug("Starting Server")
        while not stop_event.is_set():
            socks = dict(self.__poller.poll(100))

            if socks.get(self.__socket) == zmq.POLLIN:
                # there is a message to receive messages from clients
                # are not multipart so only one recv call is required
                reply = self.__socket.recv()
                self.receive_message(reply)
                sigs.tcp_message_received.send([self, reply])
                self.logger.info("Server processed message: %s" % reply)

                # now wait until a response is ready to send
                self.waiting = False
                while not self.waiting:
                    try:
                        response = self.send_queue.get(True, 0.1)
                    except Queue.Empty:
                        if stop_event.is_set():
                            break
                        continue

                    # check if we need to break up the response
                    if len(response) > self.MAX_RESPONSE_LENGTH:
                        parts = [response[i:i + self.MAX_RESPONSE_LENGTH] for i in
                                 range(0, len(response), self.MAX_RESPONSE_LENGTH)]

                        for part in parts:
                            self.__socket.send(part, zmq.SNDMORE)

                        self.__socket.send("")
                    else:
                        self.__socket.send(response)

                    self.waiting = True

        self.__socket.close()
        self.__context.term()
        self.__state_machine.force_state(ServerClosedState)
        self.logger.info("Server Closed")

    def run_client(self, stop_event):
        self.logger.info("Client starting")
        while not stop_event.is_set():
            reply = ""
            request = ""
            retries = self.REQUEST_RETRIES
            self.waiting = False

            # read from the send_queue until a message is received
            if not self.waiting:
                try:
                    request = self.send_queue.get(True, 0.1)
                except Queue.Empty:
                    time.sleep(0.1)
                    continue

                self.waiting = True
                self.__socket.send(request)

            # wait for an incoming reply
            while self.waiting:
                socks = dict(self.__poller.poll(self.REQUEST_TIMEOUT))

                # check if we are receiving
                if socks.get(self.__socket) == zmq.POLLIN:
                    # we are receiving - read the bytes
                    reply += self.__socket.recv()

                    if not reply:
                        self.logger.info("Client received empty message")
                        break

                    if not self.__socket.getsockopt(zmq.RCVMORE):
                        self.waiting = False

                else:
                    # nothing was received from the server in the timeout period
                    # reconnect with the socket and then try resending again a
                    # couple of times before just giving up :)
                    # todo disconnect and reconnect the socket
                    # self.__socket.setsockopt(zmq.LINGER, 0)
                    # self.__poller.unregister(self.__socket)
                    # self.__socket.close()

                    retries -= 1

                    if retries <= 0:
                        self.__stop_event.set()
                        self.logger.error(
                            "Unable to send message after %s attempts: %s" % (self.REQUEST_RETRIES, request))
                        raise TcpCommunicationException(
                            "Failed to receive message from client after %s attempts" % self.REQUEST_RETRIES)

                    # otherwise recreate the connection and attempt to resend
                    self.logger.info("Client attempting resend of message %s (#%s)" % (request, retries))
                    # TODO self.create_client(autorun=False)
                    # TODO self.__socket.send(request)

            # now handle the reply
            self.receive_message(reply)
            sigs.tcp_message_received.send([self, reply])
            self.logger.info("Client processed message: %s" % reply)

        # terminate the context before exiting
        self.__socket.close()
        self.__context.term()
        self.logger.info("Client Closed")


class TcpStateAction(object):
    """
    Manages a TCP action which is queued with the state machine.

    The TcpSTateMachine provides convenience methods for creating and queueing instances
    """

    # command types
    SEND = 0
    RECEIVE = 1

    def __init__(self, command_type, command):
        self.command_type = command_type
        self.command = command

    def is_send(self):
        """Returns true if this is a send command"""
        return self.command_type == TcpStateAction.SEND


class TcpStateMachine(object):
    """
    Manages TCP state and ensures the messages are processed in a thread safe manner, one at a time
    """

    def __init__(self, tcp, stop_event, initial_state):
        self.logger = logging.getLogger(__name__)
        self.__current_state = BaseState().go_to_state(tcp, initial_state)
        self.__commands = Queue.Queue()
        self.__tcp = tcp
        self.__thread = threading.Thread(target=self.run, args=[stop_event])

        # start the state machine thread
        self.__thread.daemon = True
        self.__thread.start()

    def queue_send(self, command):
        """Queues a send message"""
        self.__commands.put(TcpStateAction(TcpStateAction.SEND, command))

    def queue_receive(self, command):
        """Queues a receive message"""
        self.__commands.put(TcpStateAction(TcpStateAction.RECEIVE, command))

    def run(self, stop_event):
        self.logger.info("Starting TCP state machine")
        while not stop_event.is_set():
            # poll queue for messages
            try:
                request = self.__commands.get(True, 0.1)
            except Queue.Empty:
                time.sleep(0.1)
                continue

            # process the request
            if request.is_send():
                self.__current_state = self.__current_state.send_message(self.__tcp, request.command)
            else:
                self.__current_state = self.__current_state.receive_message(self.__tcp, request.command)

        self.logger.info("Stopping TCP state machine")

    def join(self):
        self.__thread.join()

    def is_logging(self):
        return self.__thread.is_alive() and (
            type(self.__current_state) == ClientLoggingState or type(self.__current_state) == ServerLoggingState)

    def force_state(self, state, args=None):
        self.__current_state.go_to_state(state, args)
