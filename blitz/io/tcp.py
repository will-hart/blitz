__author__ = 'Will Hart'

import Queue
import threading
import zmq

from blitz.io.client_states import *
from blitz.io.server_states import *
import blitz.io.signals as sigs


class TcpCommunicationException(Exception):
    pass


class TcpBase(object):
    REQUEST_TIMEOUT = 1500
    REQUEST_RETRIES = 3
    SERVER_ENDPOINT = "tcp://%s:%s"
    MAX_RESPONSE_LENGTH = 1024

    def __init__(self, host="localhost", port=None):
        self.__host = host
        self.__port = port
        self.current_state = None
        self.send_queue = Queue.Queue()
        self.waiting = False
        self.__poller = zmq.Poller()
        self.__stop_event = threading.Event()
        self.__state_lock = threading.RLock()

    def create_client(self, autorun=True):
        self.__context = zmq.Context(1)
        self.__socket = self.__context.socket(zmq.REQ)
        self.__socket.connect(self.SERVER_ENDPOINT % (self.__host, self.__port))
        self.current_state = BaseState().go_to_state(self, ClientInitState)

        if autorun:
            self.__run_thread(self.run_client)

    def create_server(self):
        self.__context = zmq.Context(1)
        self.__socket = self.__context.socket(zmq.REP)
        self.__socket.bind(self.SERVER_ENDPOINT % ("*", self.__port))
        self.current_state = BaseState().go_to_state(self, ServerIdleState)
        self.__run_thread(self.run_server)

    def __run_thread(self, thread_target):
        self.__poller.register(self.__socket, zmq.POLLIN)
        self.__thread = threading.Thread(target=thread_target, args=[self.__stop_event])
        self.__thread.daemon = True
        self.__thread.start()

    def is_alive(self):
        return not self.__stop_event.is_set()

    def is_logging(self):
        return type(self.current_state) == ClientLoggingState or type(self.current_state) == ServerLoggingState

    def stop(self):
        self.__stop_event.set()
        self.__thread.join()
        self.__stop_event.clear()

    def _do_send(self, message):
        self.send_queue.put(message)

    def send(self, message):
        with self.__state_lock:
            self.current_state = self.current_state.send_message(self, message)

    def process_message(self, message):
        with self.__state_lock:
            self.current_state = self.current_state.process_message(self, message)

    def run_server(self, stop_event):
        print "Starting Server"
        while not stop_event.is_set():
            socks = dict(self.__poller.poll(100))

            if socks.get(self.__socket) == zmq.POLLIN:
                # there is a message to receive messages from clients
                # are not multipart so only one recv call is required
                reply = self.__socket.recv()
                self.process_message(reply)
                sigs.tcp_message_received.send([self, reply])
                print "Server received: %s" % reply

                # now wait until a response is ready to send
                self.waiting = False
                while not self.waiting:
                    response = ""
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

                    print "Server sent: %s" % response
                    self.waiting = True

        self.__socket.close()
        self.__context.term()
        print "Server Closed"

    def run_client(self, stop_event):
        print "Client starting"
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
                print "Client sent %s" % request

            # wait for an incoming reply
            while self.waiting:
                socks = dict(self.__poller.poll(self.REQUEST_TIMEOUT))

                # check if we are receiving
                if socks.get(self.__socket) == zmq.POLLIN:
                    # we are receiving - read the bytes
                    print "Client received partial message"
                    reply += self.__socket.recv()

                    if not reply:
                        print "Client message discovered to be empty"
                        break

                    if not self.__socket.getsockopt(zmq.RCVMORE):
                        print "Client message fully received"
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
                        raise TcpCommunicationException(
                            "Failed to receive message from client after %s attempts" % self.REQUEST_RETRIES)

                    # otherwise recreate the connection and attempt to resend
                    print "Client attempting resend of message %s (#%s)" % (request, retries)
                    # TODO self.create_client(autorun=False)
                    # TODO self.__socket.send(request)

            # now handle the reply
            self.process_message(reply)
            sigs.tcp_message_received.send([self, reply])
            print "Client received %s" % reply

        # terminate the context before exiting
        self.__socket.close()
        self.__context.term()
        print "Client Closed"
