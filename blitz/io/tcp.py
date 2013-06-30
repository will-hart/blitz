__author__ = 'Will Hart'

import logging
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
        self.logger.debug("[SERVER] > Created new client connection handler")
        self._server = server
        self._stream = stream
        self._stream.set_close_callback(self._stream_closed)
        self.address = address
        self.close = False
        self.do_read()

    def _stream_closed(self):  # , *args, **kwargs):
        """A callback that triggers when the stream is closed"""
        self.logger.debug("[SERVER] > Closing client stream")
        self._server.unregister_client(self)

    def do_read(self):
        """Reads from a stream until a new line is found"""
        self.logger.debug("[SERVER] > Listening to client TCP input stream: %s:%s" % self.address)
        self._stream.read_until("\n", self._on_read)

    def _on_read(self, line):
        """Handle a read message"""
        self._server.process_message(line.replace("\n", ""))

    def send(self, message):
        """Writes a message to the socket"""
        self.logger.debug("[SERVER SENDS] > " + message)
        self._stream.write(message)


class TcpServer(tornadoTCP):
    """A server which listens for connections and maintains application state"""

    logger = logging.getLogger(__name__)

    def __init__(self, port):
        """initialise the TCP Server and register it with the IO loop"""
        super(TcpServer, self).__init__()

        # save the port
        self._port = port

        # register this class with the IO Loop
        loop = IOLoop.instance()
        loop.blitz_tcp_server = self
        self.logger.debug("[SERVER] > Created TcpServer and registered with IO loop")

        # start the server
        self.listen(port)

        self._thread = threading.Thread(target=loop.start)
        self._thread.daemon = True
        self._thread.start()
        self.logger.debug("[SERVER] > Started on port %s" % port)

        self._clients = []
        self.current_state = BaseState().go_to_state(self, ServerIdleState)

    def handle_stream(self, stream, address):
        """Handles a new client stream by spawning a client connection object"""
        self.logger.debug("[SERVER] > New client connection %s:%s" % address)
        self._clients.append(ClientConnection(self, stream, address))

    def shutdown(self):
        """Registers a callback that shuts down the tornado server"""

        # register the shutdown handler with the IO loop
        loop = IOLoop.instance()
        loop.add_callback(self._do_shutdown)

        # set the correct shutdown state
        self.current_state = self.current_state.go_to_state(self, ServerClosedState)

    def _do_shutdown(self):
        """The callback which does the shutting down"""
        loop = IOLoop.instance()
        loop.blitz_tcp_server.stop()

    def unregister_client(self, client):
        self.logger.debug("[SERVER] > Client disconnected...")
        self._clients.remove(client)

    def process_message(self, message):
        """Processes a message received from a connected client"""
        self.logger.debug("[SERVER PROCESSING] > %s" % message)
        self.current_state = self.current_state.process_message(self, message)

    def _send(self, message):
        for c in self._clients:
            c.send(message)

    def download_complete(self):
        """
        Called when the server has finished downloading to return to normal state
        """
        if type(self.current_state) is ServerDownloadingState:
            self.current_state = self.current_state.download_complete(self)


class TcpClient(object):
    """
    A TCP client which maintains a socket connection and
    sends / receives messages upon request
    """

    current_state = None
    logger = logging.getLogger(__name__)

    def __init__(self, host, port):
        """
        Connect the socket to the given port and IP
        """
        self._address = (host, port)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(self._address)
        self._socket.settimeout(0.5)
        self._outbox = []
        self.logger.debug("[CLIENT] > Created TCP Client at %s:%s" % self._address)

        # start up the state machine
        self.current_state = BaseState().enter_state(self, ClientInitState)

        # set up the listen thread
        self._stop_event = threading.Event()
        self._outbox_lock = threading.RLock()
        self._client_thread = threading.Thread(target=self.listen, args=[self._stop_event])
        self._client_thread.daemon = True
        self.logger.debug("[CLIENT] > Launching listen thread")
        self._client_thread.start()

    def listen(self, stop_event):
        self.logger.debug("[CLIENT] > Entering listen thread")
        while not stop_event.is_set():
            # send all queued messages
            with self._outbox_lock:
                for msg in self._outbox:
                    self.logger.debug("[CLIENT] > TcpClient sending: " + msg)
                    self._socket.sendall(msg + "\n")
                self._outbox = []

            # receive messages
            try:
                response = self._socket.recv(128)  # message are invariably small
                if response:
                    self.logger.debug("[CLIENT] > TcpClient has received: " + response)
                    self.process_message(response)
            except Exception:
                # TODO skip allowable exceptions and throw others
                pass
        self.logger.debug("[CLIENT] > TcpClient exiting listen thread as stop_event was triggered")

    def send(self, message):
        """
        Send the message via the current ClientState
        """
        self.current_state = self.current_state.send_message(self, message)

    def _send(self, message):
        """
        Queues the given message and read the echoed response
        """
        with self._outbox_lock:
            self._outbox.append(message)

    def disconnect(self):
        """
        Disconnects the socket
        """

        # stop the listen thread
        self._stop_event.set()
        self._client_thread.join()
        self.logger.debug("[CLIENT] > TCP Client has stopped listening")

        # close off the socket
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        self.logger.debug("[CLIENT] > TCP Client has closed socket connection")

    def process_message(self, msg):
        """
        Process a message received via TCP by using the state machine
        """
        self.current_state = self.current_state.process_message(self, msg)

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
        self.current_state = self.current_state.send_message(self, "STATUS")

    def request_download(self, session_id):
        """
        Request download of a session of data from the data logger
        """
        self.current_state = self.current_state.send_message(self, "DOWNLOAD " + str(session_id))

    def request_start(self):
        """
        Requests logging to start
        """
        self.current_state = self.current_state.send_message(self, "START")

    def request_stop(self):
        """
        Requests logging to stop
        """
        self.current_state = self.current_state.send_message(self, "STOP")

    def request_is_logging(self):
        """
        Asks the server if it is currently logging
        """
        self.current_state = self.current_state.go_to_state(self, ClientInitState)


# EXAMPLE USAGE:
#
#
# from blitz.io.tcp import TcpClient, TcpServer
# import time
#
# # set up objects
# server = TcpServer(8999)
# client = TcpClient("127.0.0.1", 8999)
# self.logger.debug(""
#
# # wait then send ACK from server
# time.sleep(1)
# server._send("NACK")
# self.logger.debug(""
#
# time.sleep(2)
# client.request_start()
