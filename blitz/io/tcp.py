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

    def _send(self, message):
        self.last_sent = message.upper()
        for c in self._clients:
            c.send(self.last_sent)

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
        # TODO this could be disabled as per https://github.com/facebook/tornado/issues/737
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow reuse
        self._socket.connect(self._address)
        self._socket.settimeout(0.5)
        self._outbox = []
        self.logger.debug("Created TCP Client at %s:%s" % self._address)

        # start up the state machine
        self.current_state = BaseState().enter_state(self, ClientInitState)

        # set up the listen thread
        self._stop_event = threading.Event()
        self._outbox_lock = threading.RLock()
        self._client_thread = threading.Thread(target=self.listen, args=[self._stop_event])
        self._client_thread.daemon = True
        self.logger.debug("Launching TcpClient listen thread")
        self._client_thread.start()

    def listen(self, stop_event):
        recv_buffer = ""

        while not stop_event.is_set():
            # send all queued messages
            with self._outbox_lock:
                for msg in self._outbox:
                    self.logger.debug("[TCP] TcpClient sending: " + msg)
                    self._socket.sendall(msg + "\n")
                self._outbox = []

            # receive messages
            try:
                recv_buffer += self._socket.recv(64)  # message are invariably small

                if recv_buffer:
                    # check if we have receved a complete message
                    if recv_buffer[-1] == "\n":
                        self.logger.debug("[TCP] TcpClient has received: " + recv_buffer[:-1])
                        self.process_message(recv_buffer[:-1])
                        recv_buffer = ""
                        return

                    # otherwise we may have a partial message
                    responses = recv_buffer.split("\n")
                    if len(responses) == 1:
                        # still waiting for complete message, continue until newline recevied
                        continue

                    # save the stub to a receive buffer
                    recv_buffer = responses[-1]

                    # process the remainder
                    for response in responses[:-1]:
                        self.logger.debug("[TCP] TcpClient has received: " + response)
                        self.process_message(response)

            except Exception:
                # TODO skip allowable exceptions and throw others
                pass

        self.logger.debug("[TCP] TcpClient exiting listen thread as stop_event was triggered")

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
            self.last_sent = message.upper()
            self._outbox.append(self.last_sent)

    def disconnect(self):
        """
        Disconnects the socket
        """

        # stop the listen thread
        self._stop_event.set()
        self._client_thread.join()
        self.logger.debug("[TCP] TCP Client has stopped listening")

        # close off the socket
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        self.logger.debug("[TCP] TCP Client has closed socket connection")

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
