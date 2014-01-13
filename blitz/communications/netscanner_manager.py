__author__ = 'Will Hart'

import logging
import Queue
import threading
import time
import zmq


class NetScannerResultWrapper(object):
    """
    A wrapper around a list of NetScanner results
    """

    # psi to kPa conversion
    psi_to_kpa = 6.89475729

    def __init__(self, results=[]):
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

    # a list of error codes from section 3.1.3, page 22 of the manual
    error_codes = {
        '00': 'Unused',
        '01': 'Undefined command received',
        '02': 'Unused by TCP/IP',
        '03': 'Input buffer overrun',
        '04': 'Invalid ASCII character received',
        '05': 'Data field error',
        '06': 'Unused by TCP/IP',
        '07': 'Specified limits invalid',
        '08': 'NetScanner error; invalid parameter',
        '09': 'Insufficient source air to shift calibration value',
        '0A': 'Calibration value not in requested position',
    }

    # message codes sent to/from the device
    response_codes = {
        'A': 'ACK',
        'N': 'NAK'
    }

    # commands that can be sent to the unit
    commands = {
        'A': 'Power up clear',
        'B': 'Reset',
        'C': 'Configure/Control multi-point calibration',
        'V': 'Read transducer voltages',
        'Z': 'Calculate and set gains',
        'a': 'Read transducer raw A/D counts',
        'b': 'Read high speed data',
        'h': 'Calculate and set offsets',
        'm': 'Read temperature A/D counts',
        'n': 'Read temperature voltages',
        'q': 'Read module status',
        'r': 'Read high precision data',
        't': 'Read transducer temperatures',
        'u': 'Read internal coefficients',
        'v': 'Download internal coefficients',
        'w': 'Set/Do operating commands'
    }

    SERVER_ENDPOINT = "tcp://%s:%s"

    logger = logging.getLogger(__name__)

    READ_DATA = 'r'

    def __init__(self, host, port):
        """
        Initialises a NetScannerManager which connects a TCP/IP connection to the device

        :param host: The host IP address of the NetScanner device
        :param port: The port of the NetScanner device
        """

        self.__host = host
        self.__port = port
        self.receive_queue = Queue.Queue()

        self.__poller = zmq.Poller()
        self.__stop_event = threading.Event()
        self.__context = zmq.Context(1)
        self.__socket = self.__context.socket(zmq.REQ)
        self.__socket.connect(self.SERVER_ENDPOINT % (self.__host, self.__port))

        self.__run_thread(self.__run_client)

    def __run_thread(self, thread_target):
        self.__poller.register(self.__socket, zmq.POLLIN)
        self.__thread = threading.Thread(target=thread_target, args=[self.__stop_event])
        self.__thread.daemon = True
        self.__thread.start()

    def run_client(self, stop_event):
        self.logger.info("NetScanner interface starting")
        while not stop_event.is_set():
            reply = ""
            request = ""
            self.waiting = False

            # read from the send_queue until a message is received
            if not self.waiting:
                # use approx 10Hz sample rate
                time.sleep(0.1)
                self.__socket.send(self.READ_DATA)

                # set flag indicating we are waiting for a response
                self.waiting = True

            # wait for an incoming reply
            while self.waiting:
                # find a list of sockets ready to return information
                socks = dict(self.__poller.poll(self.REQUEST_TIMEOUT))

                # check if our socket is in the list
                if socks.get(self.__socket) == zmq.POLLIN:
                    # we are receiving - read the bytes
                    reply += self.__socket.recv()

                    if not reply:
                        self.logger.info("NetScanner received empty message")
                        break

                    if not self.__socket.getsockopt(zmq.RCVMORE):
                        self.waiting = False

                else:
                    # for some reason our socket is not ready to receive
                    self.__stop_event.set()
                    self.logger.error("Error receiving information from NetScanner, aborting")

            # now handle the reply
            self.receive_message(reply)
            # TODO sigs.tcp_message_received.send([self, reply])
            self.logger.info("NetScanner received message: %s" % reply)

        # terminate the context before exiting
        self.__socket.close()
        self.__context.term()
        self.logger.info("NetScanner client closed")

    def receive_message(self, message):
        """
        Receives and handles a new message received via TCP

        :param message: the message that was received
        """
        if (message[0] in self.response_codes.keys()):
            self.logger.info("NetScanner received message: %s" % self.response_codes[message[0]])
        else:
            results = [float(x) for x in message.split(" ")]
            self.receive_queue.put(NetScannerResultWrapper(results))

    def stop_client(self):
        """
        Stops a client from polling the NetScanner by setting the stop_event
        """
        self.__stop_event.set()

    def get_channels(self):
        """
        Gets the FIFO based list of channel pressures
        """

        if not self.receive_queue.empty():
            return self.receive_queue.get().results()
        else:
            return []
