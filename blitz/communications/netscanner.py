"""
    from blitz.communications.netscanner_manager import NetScannerManager as nm
    import time
    mynm = nm("200.200.18.190")
    time.sleep(10)
    mynm.stop_client()
"""

__author__ = 'Will Hart'

import datetime
import logging
import Queue
import socket
import threading
import time

from blitz.communications.signals import logging_started


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
    INIT_SEQUENCE = [
        ('A', 'NOP connection check'),
        ('B', 'reset device'),
        ('v01101 6.894757', 'use kPa'),
        ('h', 'zero offsets'),
        ('b', 'digital read data')
    ]

    REQUEST_TIMEOUT = 3.0

    SAMPLE_FREQUENCY = 2.0

    logger = logging.getLogger(__name__)

    def __init__(self, database, host, board_id="0A", port=9000):
        """
        Initialises a NetScannerManager which connects a TCP/IP connection to the device

        :param host: The host IP address of the NetScanner device
        :param port: The port of the NetScanner device
        :param database: The database to use to save serial data
        """

        self.__host = host
        self.__port = port
        self.__data = database
        self.__board_id = board_id
        self.receive_queue = Queue.Queue()
        self.__stop_event = threading.Event()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.settimeout(self.REQUEST_TIMEOUT)
        self.__run_thread(self.run_client)
        self.__thread = None
        self.__logging_start = datetime.datetime.now()

        logging_started.connect(self.start_logging)

    def __run_thread(self, thread_target):
        self.__thread = threading.Thread(target=thread_target, args=[self.__stop_event])
        self.__thread.daemon = True
        self.__thread.start()

    def run_client(self, stop_event):
        try:
            self.__socket.connect((self.__host, self.__port))
        except Exception as e:
            self.logger.critical("Unable to start NetScanner:")
            self.logger.critical(e)
            return

        self.__logging_start = datetime.datetime.now()

        current_state = 0
        self.logger.debug("NetScanner starting polling loop")

        while not stop_event.is_set():
            self.__socket.send(self.INIT_SEQUENCE[current_state][0])
            if current_state < len(self.INIT_SEQUENCE) - 1:
                self.logger.debug("Netscanner sent {0} message".format(self.INIT_SEQUENCE[current_state][1]))
            data = self.__socket.recv(1024)
            self.receive_message(data)

            if current_state < len(self.INIT_SEQUENCE) - 1:
                current_state += 1
            else:
                # sample at approximately 2 Hz
                time.sleep(1.0 / self.SAMPLE_FREQUENCY)

        # terminate the context before exiting
        self.__socket.close()
        self.logger.debug("NetScanner terminated")

    def start_logging(self, args):
        """
        Stores the current time when data logging commences so the correct timestamp can be provided to messages
        """
        self.__logging_start = datetime.datetime.now()

    def receive_message(self, message):
        """
        Receives and handles a new message received via TCP

        :param message: the message that was received
        """
        if message == "A":
            self.logger.debug("NetScanner received ACK from device")
        else:
            if self.__data:
                delta_t = (datetime.datetime.now() - self.__logging_start).microseconds / 1000.0
                delta_t = hex(delta_t).rjust(8, '0').upper()
                results = [message[i:i+4] for i in xrange(0, len(message), 4)]

                if len(results) != 16:
                    self.logger.warning(
                        "Received incomplete NetScanner message, only read %s channels (not 16)" % len(results))
                else:
                    # hackity hack
                    self.__data.queue(
                        self.__board_id + "0ABO" + delta_t + results[0] + results[1] + results[2] + results[3])
                    self.__data.queue(
                        self.__board_id + "0AA8" + delta_t + results[4] + results[5] + results[6] + results[7])
                    self.__data.queue(
                        self.__board_id + "0AA4" + delta_t + results[8] + results[9] + results[10] + results[11])
                    self.__data.queue(
                        self.__board_id + "0AA2" + delta_t + results[12] + results[13] + results[14] + results[15])

    def stop_client(self):
        """
        Stops a client from polling the NetScanner by setting the stop_event
        """
        self.__stop_event.set()
        self.__thread.join()
        self.logger.debug("NetScanner thread stopped")
