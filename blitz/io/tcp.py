__author__ = 'Will Hart'

import socket
import threading
from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer as tornadoTCP

from blitz.io.client_states import *
from blitz.io.server_states import *


class ClientConnection(object):
    """An object which handles a client connection"""

    def __init__(self, server, stream, address):
        """Instantiates a new client connection"""
        print"Created new client connection"
        self._server = server
        self._stream = stream
        self._stream.set_close_callback(self._stream_closed)
        self.address = True
        self.close = False
        self.do_read()

    def _stream_closed(self, *args, **kwargs):
        """A callback that triggers when the stream is closed"""
        print "Closing client stream"
        self._server.unregister_client(self)

    def do_read(self):
        """Reads from a stream until a new line is found"""
        print "Reading from client stream"
        self._stream.read_until("\n", self._on_read)

    def _on_read(self, line):
        """Handle a read message"""
        self._server.process_message(line.replace("\n",""))
        #self.do_read()

    def send(self, message):
        """Writes a message to the socket"""
        print"Writing message: " + message
        self._stream.write(message)


class TcpServer(tornadoTCP):
    """A server which listens for connections and maintains application state"""

    def __init__(self, port):
        """initialise the TCP Server and register it with the IO loop"""
        super(TcpServer, self).__init__()

        # save the port
        self._port = port

        # register this class with the IO Loop
        loop = IOLoop.instance()
        loop.blitz_tcp_server = self
        print"Created TcpServer and registered with IO loop"

        # start the server
        self.listen(port)

        self._thread = threading.Thread(target=loop.start)
        self._thread.daemon = True
        self._thread.start()
        print"Started server on port %s" % port

        self._clients = []
        self.current_state = BaseState().go_to_state(self, ServerIdleState)

    def handle_stream(self, stream, address):
        """Handles a new client stream by spawning a client connection object"""
        print"New client connection %s:%s" % address
        self._clients.append(ClientConnection(self, stream, address))

    def shutdown(self):
        """Registers a callback that shuts down the tornado server"""
        loop = IOLoop.instance()
        loop.add_callback(self._do_shutdown)

    def _do_shutdown(self):
        """The callback which does the shutting down"""
        loop = IOLoop.instance()
        loop.blitz_tcp_server.stop()

    def unregister_client(self, client):
        print"Client disconnected..."
        self._clients.remove(client)

    def process_message(self, message):
        """Processes a message received from a connected client"""
        print " > %s" % message

    def send(self, message):
        print "Sending > " + message
        for c in self._clients:
            print " (do send) "
            c.send(message)


class TcpClient(object):
    """
    A TCP client which maintains a socket connection and
    sends / receives messages upon request
    """

    current_state = None

    def __init__(self, address):
        """
        Connect the socket to the given port and IP
        """
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(address)
        self._socket.settimeout(0.5)
        self.connected = True
        self._outbox = []

        # start up the state machine
        self.current_state = BaseState().enter_state(self, ClientInitState)

    def send(self, message):
        """
        Send the message via the current ClientState
        """
        self.current_state = self.current_state.send_message(self, message)

    def _send(self, message):
        """
        Queues the given message and read the echoed response
        """
        self._outbox.append(message)

        if not self.connected:
            raise Exception("Attempted to send data on a closed socket!")

        try:
            print "Sending: {}".format(message)
            self._socket.sendall(message)
            response = self._socket.recv(1024)
            print "Received: {}".format(response)
            self.process_message(response)
        except Exception as e:
            print "An error occurred - {}".format(e)
            print " >> Closing the socket"
            self._socket.close()

    def disconnect(self):
        """
        Disconnects the socket
        """
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        self.connected = False

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
        # TODO
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
# from blitz.io.tcp import TcpServer, TcpClient
# import threading
#
# server = TcpServer(('', 8999))
# server.start()
#
# client = TcpClient(("127.0.0.1", 8999))
# client.send("From Client")
