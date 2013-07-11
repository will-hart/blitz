__author__ = 'Will Hart'

import logging
import Queue
import socket
import threading
from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer as tornadoTCP
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


class ClientConnection(object):
    """An object which handles a client connection"""

    logger = logging.getLogger(__name__)

    def __init__(self, server, stream, address):
        """Instantiates a new client connection"""
        self.logger.debug("[TCP] Created new client connection handler")
        self._server = server
        self._stream = stream
        self._stream.set_close_callback(self._stream_closed)
        self.address = address
        self.closing = False
        self.do_read()

    def _stream_closed(self):  # , *args, **kwargs):
        """A callback that triggers when the stream is closed"""
        self.logger.debug("[TCP] Closing client stream")
        self._server.unregister_client(self)

    def do_read(self):
        """Reads from a stream until a new line is found"""
        self._stream.read_until("\n", self._on_read)

    def _on_read(self, line):
        """Handle a read message"""
        self.logger.critical("Handling read message: %s" % line)
        self._server.process_message(line.replace("\n", ""))

        if not self.closing:
            self.do_read()  # listen for the next message

    def send(self, message):
        """Writes a message to the socket"""
        self.logger.debug("[TCP] > " + message)
        self._stream.write(message + "\n")


class TcpServer(tornadoTCP):
    """A server which listens for connections and maintains application state"""

    logger = logging.getLogger(__name__)
    is_running = False

    def __init__(self, port):
        """initialise the TCP Server and register it with the IO loop"""
        super(TcpServer, self).__init__()

        # save the port
        self._port = port

        # register this class with the IO Loop
        loop = IOLoop.instance()
        loop.blitz_tcp_server = self

        # start the server
        self.listen(port)

        self._thread = threading.Thread(target=loop.start)
        self._thread.daemon = True
        self._thread.start()
        self.is_running = True

        self._clients = []
        self.current_state = BaseState().go_to_state(self, ServerIdleState)
        self.logger.debug("TcpServer listening on port %s" % port)

    def handle_stream(self, stream, address):
        """Handles a new client stream by spawning a client connection object"""
        self.logger.info("[TCP] New client connection %s:%s" % address)
        self._clients.append(ClientConnection(self, stream, address))

    def shutdown(self):
        """Registers a callback that shuts down the tornado server"""

        # register the shutdown handler with the IO loop
        IOLoop.instance().add_callback(self._do_shutdown)

        # set the correct shutdown state
        self.current_state = self.current_state.go_to_state(self, ServerClosedState)

        # stop all the clients from listening
        for client in self._clients:
            client.closing = True

    def _do_shutdown(self):
        """The callback which does the shutting down"""
        loop = IOLoop.instance()
        loop.blitz_tcp_server.stop()

    def unregister_client(self, client):
        self.logger.info("[TCP] Client %s:%s disconnected..." % client.address)
        self._clients.remove(client)

    def process_message(self, message):
        """Processes a message received from a connected client"""
        self.logger.debug("[SERVER PROCESSING] > %s" % message)
        self.current_state = self.current_state.process_message(self, message)

    def _do_send(self, message):
        self.last_sent = message.upper()
        for c in self._clients:
            c.send(self.last_sent)

    def download_complete(self):
        """
        Called when the server has finished downloading to return to normal state
        """
        if type(self.current_state) is ServerDownloadingState:
            self.current_state = self.current_state.download_complete(self)

    def send(self, message):
        """Sends the given message through the current_state ServerState"""
        self.current_state = self.current_state.send_message(self, message)

#
# A threaded TCP client based on
# http://eli.thegreenplace.net/2011/05/18/code-sample-socket-client-thread-in-python/
#
class TcpClientCommand(object):
    """ A command to the client thread.
        Each command type has its associated data:

        CONNECT:    (host, port) tuple
        SEND:       Data string
        RECEIVE:    None
        CLOSE:      None
    """
    CONNECT, SEND, RECEIVE, CLOSE, START, STOP, LOGGING = range(7)

    def __init__(self, cmd, data=None):
        self.type = cmd
        self.data = data


class TcpClientReply(object):
    """ A reply from the client thread.
        Each reply type has its associated data:

        ERROR:      The error string
        SUCCESS:    Depends on the command - for RECEIVE it's the received
                    data string, for others None.
    """
    ERROR, SUCCESS, MESSAGE = range(3)

    def __init__(self, cmd, data=None):
        self.type = cmd
        self.data = data


class TcpClient(threading.Thread):
    """
    A TCP client which maintains a socket connection and
    sends / receives messages upon request
    """

    current_state = None
    logger = logging.getLogger(__name__)

    def __init__(self, host, port, inbox=None, outbox=None):
        """
        Connect the socket to the given port and IP
        """
        super(TcpClient, self).__init__()
        self.__address = (host, port)
        self.command_queue = inbox or Queue.Queue()
        self.response_queue = outbox or Queue.Queue()
        self.alive = threading.Event()
        self.alive.set()
        self._socket = None
        self.__connected = False
        self.state_lock = threading.Lock()
        self.logger.debug("Created TCP Client at %s:%s" % self.__address)

        # set up the command handlers
        self.handlers = {
            TcpClientCommand.CONNECT: self.__handle_connect,
            TcpClientCommand.CLOSE: self.__handle_close,
            TcpClientCommand.SEND: self.__handle_send,
            TcpClientCommand.RECEIVE: self.__handle_receive
        }

    def run(self):
        """
        Runs the TcpClient, listening for events
        """
        self.logger.info("Entering TcpClient thread")

        while self.alive.is_set():
            try:
                # try to get a command and handle it
                cmd = self.command_queue.get(True, 0.1)
                self.handlers[cmd.type](cmd)
            except Queue.Empty:
                # this is ok - we can continue
                # other exceptions should be thrown
                continue

    def join(self, timeout=None):
        """
        Closes the thread and blocks until this is done
        """
        self.logger.debug("Attempting to close TcpClient thread")
        self.alive.clear()
        threading.Thread.join(self, timeout)
        self.logger.debug("TcpClient thread closed")

    def __handle_connect(self, cmd):
        """
        Connects to a TCP Server
        :param cmd: The connection command
        """
        self.logger.debug("TcpClient handling CONNECT command")
        try:
            self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__socket.connect(self.__address)
            self.response_queue.put(self.__success_reply())

            # start up the state machine
            with self.state_lock:
                self.current_state = BaseState().go_to_state(self, ClientInitState)

            self.__connected = True

        except IOError as e:
            self.logger.error("Error in TcpClient.CONNECT - " + str(e))
            self.response_queue.put(self.__error_reply(str(e)))
            self.__connected = False

    def __handle_close(self, cmd):
        """
        Closes the TCP socket
        :param cmd: The close command
        """
        self.logger.debug("TcpClient handling CLOSE command")
        self.__socket.close()
        reply = self.__success_reply()
        self.response_queue.put(reply)
        self.__connected = False

    def __handle_send(self, cmd):
        """
        Sends a message to the TCP Server
        :param cmd: The command object, where cmd.data is the message to send
        """
        self.logger.debug("TcpClient handling SEND command - " + cmd.data)
        try:
            self.__socket.sendall(cmd.data.upper() + "\n")
            self.response_queue.put(self.__success_reply())
            self.command_queue.put(TcpClientCommand(TcpClientCommand.RECEIVE))
        except IOError as e:
            self.logger.error("Error in TcpClient.SEND - " + str(e))
            self.response_queue.put(self.__error_reply(str(e)))

    def __handle_receive(self, cmd):
        """
        Receives from the socket
        :param cmd: The command to receive
        """
        self.logger.debug("TcpClient handling RECEIVE command")
        try:
            data = self.__receive_until_newline()
            self.process_message(data)
        except IOError as e:
            self.logger.error("Error in TcpClient.RECEIVE - " + str(e))
            self.response_queue.put(self.__error_reply(str(e)))

    def __receive_until_newline(self):
        """
        Receives data until a new line is found
        """
        message = ""
        separator = "\n"
        while True:
            chunk = self.__socket.recv(1)
            if chunk == "" or chunk == separator:
                break
            message += chunk
        self.logger.debug("TcpClient received raw message - " + message)
        return message

    def __read_reply(self, log_message="TCP Operation", timeout=2, blocking=True):
        """Reads a reply from the TCP outbox queue and raises log messages accordingly"""
        try:
            reply = self.response_queue.get(blocking, timeout)
            if reply.type == TcpClientReply.SUCCESS:
                self.logger.debug("Successfully completed " + log_message)
            else:
                self.logger.error("Error in TCP Client during " + log_message + " - " + reply.data)
        except Queue.Empty:
            self.logger.warning("Unable to complete " + log_message + " before timeout")

    def __success_reply(self, data=None):
        return TcpClientReply(TcpClientReply.SUCCESS, data)

    def __error_reply(self, data):
        return TcpClientReply(TcpClientReply.ERROR, data)

    def __message_reply(self, payload):
        return TcpClientReply(TcpClientReply.MESSAGE, payload)

    def _do_send(self, message):
        """
        Queues the given message and read the echoed response
        """
        self.last_sent = message.upper()
        self.command_queue.put(TcpClientCommand(TcpClientCommand.SEND, message))
        self.__read_reply("send request")

    def connect(self, host=None, port=None):
        """Connects to the IP and port given in the constructor"""

        # save new connection details if received
        if host is not None:
            self.__address = (host, self.__address[1])
        if port is not None:
            self.__address = (self.__address[0], port)

        # connect
        self.logger.info("Creating TCP Client Connection to %s:%s" % self.__address)
        self.command_queue.put(TcpClientCommand(TcpClientCommand.CONNECT, None))
        self.__read_reply("connection request")

    def send(self, message):
        """
        Send the message via the current ClientState
        """
        with self.state_lock:
            self.current_state = self.current_state.send_message(self, message)

    def disconnect(self):
        """
        Disconnects the socket
        """
        self.logger.info("Stopping TCP Client")
        return self.join()

    def process_message(self, msg):
        """
        Process a message received via TCP by using the state machine
        """
        with self.state_lock:
            self.current_state = self.current_state.process_message(self, msg)
        self.logger.debug("Finished processing message - %s" % msg)

    def parse_reading(self, msg):
        """
        Parses a reading received from a state machine using ExpansionBoard
        classes.
        """
        # raise the signal and let subscribers handle it
        sigs.data_line_received.send(msg)

    def request_status(self):
        """
        Request a status update from the data logger
        """
        with self.state_lock:
            self.current_state = self.current_state.send_message(self, CommunicationCodes.Update)

    def request_session_list(self):
        with self.state_lock:
            self.current_state = self.current_state.send_message(self, CommunicationCodes.GetSessions)

    def request_download(self, session_id):
        """
        Request download of a session of data from the data logger
        """
        with self.state_lock:
            self.current_state = self.current_state.send_message(self, CommunicationCodes.composite(
                CommunicationCodes.Download, session_id))

    def request_start(self):
        """
        Requests logging to start
        """
        with self.state_lock:
            self.current_state = self.current_state.send_message(self, CommunicationCodes.Start)

    def request_stop(self):
        """
        Requests logging to stop
        """
        with self.state_lock:
            self.current_state = self.current_state.send_message(self, CommunicationCodes.Stop)

    def request_is_logging(self):
        """
        Asks the server if it is currently logging
        """
        # TODO what the hell is this meant to do? should actually send a status command!
        with self.state_lock:
            self.current_state = self.current_state.go_to_state(self, ClientInitState)

    def is_logging(self):
        """
        Returns True if the client is currently in logging state
        """
        return type(self.current_state) is ClientLoggingState

    def is_busy(self):
        """
        Returns True if the Tcp Client currently has queued commands, False otherwise
        """
        return self.command_queue.empty()

    def is_connected(self):
        """
        Returns True if the TCP client is currently busy
        """
        return self.__connected

