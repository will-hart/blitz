"""
    from blitz.communications.netscanner_manager import NetScannerManager as nm
    import time
    mynm = nm("200.200.18.190")
    time.sleep(10)
    mynm.stop_client()
"""

__author__ = 'Will Hart'

import logging
import Queue
import threading
import socket
import time


class NetScannerResultWrapper(object):
    """
    A wrapper around a list of NetScanner results
    """

    # psi to kPa conversion
    psi_to_kpa = 6.89475729

    def __init__(self, results=None):
        self.channels = [x * self.psi_to_kpa for x in results]

    def channel(self, channel_id):
        """
        Returns a single channel from the results, or -1 if the channel number is invalid

        :param channel_id: The channel number to get the pressure value for
        :returns: A single float value, indicating the channel pressure reading in kPa
        """
        if channel_id < 0 or channel_id > len(self.channels):
            return -1
        return self.channels[channel_id]

    def results(self):
        """
        Returns all of the results from this NetScanner dataset

        :returns: A list of float values indicating kPa pressures
        """
        return self.channels


class NetScannerManager(object):
    """
    A class which handles decoding and interpretation of TCP messages received
    from a NetScanner 9116 or 8IFC device.
    """

    # Steps in startup:
    #  1. Device handshake
    #  2. Device reset
    #  3. Set standard units (e.g kPa)
    #  4. Calibrate offset (i.e. set ambient to 0)
    #  5. Query data from all channels in decimal format (repeat)
    INIT_SEQUENCE = ['A', 'B', 'v01101 6.894757', 'h', 'rFFFF0']

    REQUEST_TIMEOUT = 3.0

    SAMPLE_FREQUENCY = 2.0

    logger = logging.getLogger(__name__)

    def __init__(self, host, port=9000):
        """
        Initialises a NetScannerManager which connects a TCP/IP connection to the device

        :param host: The host IP address of the NetScanner device
        :param port: The port of the NetScanner device
        """

        self.__host = host
        self.__port = port
        self.receive_queue = Queue.Queue()
        self.__stop_event = threading.Event()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.settimeout(self.REQUEST_TIMEOUT)
        self.__run_thread(self.run_client)

    def __run_thread(self, thread_target):
        self.__thread = threading.Thread(target=thread_target, args=[self.__stop_event])
        self.__thread.daemon = True
        self.__thread.start()

    def run_client(self, stop_event):
        print ("NetScanner interface starting")
        self.__socket.connect((self.__host, self.__port))
        current_state = 0
        print ("Netscanner connected")

        while not stop_event.is_set():
            self.__socket.send(self.INIT_SEQUENCE[current_state])
            data = self.__socket.recv(1024)
            self.receive_message(data)

            if current_state < len(self.INIT_SEQUENCE) - 1:
                current_state += 1
            else:
                # sample at approximately 2 Hz
                time.sleep(1.0 / self.SAMPLE_FREQUENCY)

        # terminate the context before exiting
        print ("Terminating NetScanner thread")
        self.__socket.close()
        print ("NetScanner terminated")

    def receive_message(self, message):
        """
        Receives and handles a new message received via TCP

        :param message: the message that was received
        """
        print "Message length %s received" % len(message)
        if message[0] in self.response_codes.keys():
            print ("NetScanner received message: %s" % self.response_codes[message[0]])
        else:
            results = [float(x) for x in message.split(" ")]
            self.receive_queue.put(NetScannerResultWrapper(results))

    def stop_client(self):
        """
        Stops a client from polling the NetScanner by setting the stop_event
        """
        self.__stop_event.set()
        self.__thread.join()
        print ("NetScanner thread stopped")

    def get_channels(self):
        """
        Gets the FIFO based list of channel pressures
        """

        if not self.receive_queue.empty():
            return self.receive_queue.get().results()
        else:
            return []
