__author__ = 'Will Hart'

import socket
import threading
import SocketServer

from blitz.io.client_states import *


class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    """
    A class for handling TCP requests
    """

    def handle(self):
        """
        Handle the request - in this case just echo the result
        """
        while True:
            data = self.request.recv(1024)

            # check if the connection is still alive
            if not data:
                break
            cur_thread = threading.current_thread()

            response = "{}: {}".format(cur_thread.name, data)

            # echo the response back to the server
            self.request.sendall(response)


class TcpServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, address):
        """
        Creates a new TCP server
        """
        SocketServer.TCPServer.__init__(self, address, ThreadedTCPRequestHandler)


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
        self.connected = True

        # start up the state machine
        self.current_state = BaseState().enter_state(self, InitState)

    def send(self, message):
        """
        Send the given message and read the echoed response
        """

        if not self.connected:
            raise Exception("Attempted to send data on a closed socket!")

        try:
            print "Sending: {}".format(message)
            self._socket.sendall(message)
            response = self._socket.recv(1024)
            print "Received: {}".format(response)
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
        self.current_state = self.current_state.go_to_state(self, InitState)


# EXAMPLE USAGE:

# from blitz.io.tcp import TcpServer, TcpClient
# ip = "localhost"
# port = 8989
# addr = (ip, port)
#
# import threading
# server = TcpServer(addr)
# server_thread = threading.Thread(target=server.serve_forever)
# server_thread.daemon = True
# server_thread.start()
#
# client = TcpClient(addr)
# client.send("Hello World 1")
# client.send("Hello World 2")
# client.send("Hello World 3")

