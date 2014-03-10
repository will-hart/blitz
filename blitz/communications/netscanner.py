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

from blitz.communications.signals import logging_started, logging_stopped


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
        ('rFFFF0', 'digital read data') # or b for binary format
    ]

    REQUEST_TIMEOUT = 5.0

    SAMPLE_FREQUENCY = 2.0

    MAX_RETRIES = 10

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
        self.board_id = board_id
        self.receive_queue = Queue.Queue()
        self.__stop_event = threading.Event()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.settimeout(self.REQUEST_TIMEOUT)
        self.__run_thread(self.run_client)
        self.__thread = None
        self.__logging_start = datetime.datetime.now()
        self.__logging = False
        self.__logging_lock = threading.RLock()

        logging_started.connect(self.start_logging)
        logging_stopped.connect(self.stop_logging)

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
        retries = 0
        self.logger.debug("NetScanner starting polling loop")

        while not stop_event.is_set():

            if self.INIT_SEQUENCE[current_state][0] == self.INIT_SEQUENCE[-1][0]:

                skip = False

                # the handshake is finished, check if we should be logging
                with self.__logging_lock:
                    if not self.__logging:
                        skip = True

                if skip:
                    time.sleep(1.0 / self.SAMPLE_FREQUENCY)
                    continue

            self.__socket.send(self.INIT_SEQUENCE[current_state][0])
            if current_state < len(self.INIT_SEQUENCE) - 1:
                self.logger.debug("Netscanner sent {0} message".format(self.INIT_SEQUENCE[current_state][1]))

            try:
                data = self.__socket.recv(1024)
            except Exception as e:
                self.logger.warning("NetScanner receive failed with exception... retrying. Exception was:")
                self.logger.warning(e)
                retries += 1

                if retries > self.MAX_RETRIES:
                    self.logger.error("Max retries on NetScanner exceeded. Aborting")
                    stop_event.set()
            else:
                self.receive_message(data)
                retries = 0

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

        with self.__logging_lock:
            self.__logging = True

    def stop_logging(self, args):
        """
        Stops the NetScanner manager from sampling from the NetScanner device
        """
        with self.__logging_lock:
            self.__logging = False

    def receive_message(self, message):
        """
        Receives and handles a new message received via TCP

        :param message: the message that was received
        """
        delta_t = 0

        if message == "A":
            self.logger.debug("NetScanner received ACK from device")
        else:
            if self.__data:
                delta_t = (datetime.datetime.now() - self.__logging_start).total_seconds() * 1000.0
                delta_t = hex(int(delta_t))[2:].rjust(8, '0').upper()

                raw = message.decode('hex').split()
                if len(raw) == 16:
                    out_message = ""
                    for r in raw:
                        out_message += hex(int(float(r) * 1e6))[2:].rjust(8, "0").upper()

                    self.__data.queue(self.board_id + "50" + delta_t + out_message)
                else:
                    self.logger.debug("Received {0} variables from the NetScanner device, ignoring".format(len(raw)))

    def stop_client(self):
        """
        Stops a client from polling the NetScanner by setting the stop_event
        """
        self.__stop_event.set()
        self.__thread.join()
        self.logger.debug("NetScanner thread stopped")
