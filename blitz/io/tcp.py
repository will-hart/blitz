__author__ = 'Will Hart'

import logging
import Queue
import socket
import threading
from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer as tornadoTCP

from blitz.io.client_states import *
from blitz.io.server_states import *


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
        self.logger.debug("TcpServer __init__")

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


#
# A threaded TCP client - http://eli.thegreenplace.net/2011/05/18/code-sample-socket-client-thread-in-python/
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
        self.inbox = inbox or Queue.Queue()
        self.outbox = outbox or Queue.Queue()
        self.alive = threading.Event()
        self.alive.set()
        self._socket = None
        self.logger.debug("Created TCP Client at %s:%s" % self.__address)

        # start up the state machine
        self.current_state = BaseState().enter_state(self, ClientInitState)

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
                cmd = self.inbox.get(True, 0.1)
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
            self.outbox.put(self.__success_reply())
        except IOError as e:
            self.logger.error("Error in TcpClient.CONNECT - " + str(e))
            self.outbox.put(self.__error_reply(str(e)))

    def __handle_close(self, cmd):
        """
        Closes the TCP socket
        :param cmd: The close command
        """
        self.logger.debug("TcpClient handling CLOSE command")
        self.__socket.close()
        reply = self.__success_reply()
        self.outbox.put(reply)

    def __handle_send(self, cmd):
        """
        Sends a message to the TCP Server
        :param cmd: The command object, where cmd.data is the message to send
        """
        self.logger.debug("TcpClient handling SEND command - " + cmd.data)
        try:
            self.__socket.sendall(cmd.data)
            self.outbox.put(self.__success_reply())
        except IOError as e:
            self.logger.error("Error in TcpClient.SEND - " + str(e))
            self.outbox.put(self.__error_reply(str(e)))

    def __handle_receive(self, cmd):
        """
        Receives from the socket
        :param cmd: The command to receive
        """
        self.logger.debug("TcpClient handling RECEIVE command - " + cmd.data)
        try:
            data = self.__receive_until_newline()
            self.process_message(data)
        except IOError as e:
            self.logger.error("Error in TcpClient.RECEIVE - " + str(e))
            self.outbox.put(self.__error_reply(str(e)))

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

    def connect(self, host=None, port=None):
        """Connects to the IP and port given in the constructor"""

        # save new connection details if received
        if host is not None:
            self.__address = (host, self.__address[1])
        if port is not None:
            self.__address = (self.__address[0], port)

        # connect
        self.logger.info("Creating TCP Client Connection to %s:%s" % self.__address)
        self.inbox.put(TcpClientCommand(TcpClientCommand.CONNECT, None))
        self.__read_reply("connection request")

    def send(self, message):
        """
        Send the message via the current ClientState
        """
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
        self.current_state = self.current_state.process_message(self, msg)

    def _do_send(self, message):
        """
        Queues the given message and read the echoed response
        """
        self.last_sent = message.upper()
        self.inbox.put(TcpClientCommand(TcpClientCommand.SEND, message.upper()))
        self.__read_reply("send request")

    def __read_reply(self, log_message="TCP Operation", timeout=2, blocking=True):
        """Reads a reply from the TCP outbox queue and raises log messages accordingly"""
        try:
            reply = self.outbox.get(blocking, timeout)
            if reply.type == TcpClientReply.SUCCESS:
                self.logger.debug("Successfully completed " + log_message)
            else:
                self.logger.error("Error in TCP Client during " + log_message + " - " + reply.data)
        except Queue.Empty:
            self.logger.warning("Unable to complete " + log_message + " before timeout")

    def parse_reading(self, msg):
        """
        Parses a reading received from a state machine using ExpansionBoard
        classes.
        """
        # TODO - pass to a BoardManager for parsing and storage in the database
        pass

    def request_status(self):
        """
        Request a status update from the data logger
        """
        self.current_state = self.current_state.send_message(self, CommunicationCodes.Update)

    def request_download(self, session_id):
        """
        Request download of a session of data from the data logger
        """
        self.current_state = self.current_state.send_message(self, CommunicationCodes.composite(
            CommunicationCodes.Download, session_id))

    def request_start(self):
        """
        Requests logging to start
        """
        self.current_state = self.current_state.send_message(self, CommunicationCodes.Start)

    def request_stop(self):
        """
        Requests logging to stop
        """
        self.current_state = self.current_state.send_message(self, CommunicationCodes.Stop)

    def request_is_logging(self):
        """
        Asks the server if it is currently logging
        """
        self.current_state = self.current_state.go_to_state(self, ClientInitState)

    def is_logging(self):
        """
        Returns True if the client is currently in logging state
        """
        return type(self.current_state) is ClientLoggingState

    def __success_reply(self, data=None):
        return TcpClientReply(TcpClientReply.SUCCESS, data)

    def __error_reply(self, data):
        return TcpClientReply(TcpClientReply.ERROR, data)

    def __message_reply(self, payload):
        return TcpClientReply(TcpClientReply.MESSAGE, payload)
