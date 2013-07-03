__author__ = 'Will Hart'

import logging
import threading
import time

from blitz.constants import SerialUpdatePeriod
from blitz.data.database import DatabaseServer
from blitz.utilities import generate_tcp_server_fixtures


class SerialManager(object):
    """
    Manages serial (RS232, SPI or I2C) communications with expansion
    boards.  It has both a monitoring loop and an "outbox" which it
    uses for sending information.
    """

    __outbox_lock = threading.Lock()
    __queue_lock = threading.Lock()
    __instance = None
    __data = None
    __stop_event = None
    __serial_thread = None
    __listen_thread = None

    logger = logging.getLogger(__name__)

    def __init__(self):
        """
        Follows a singleton pattern and prevents instantiation of more than one Serial Manager.
        """

        if SerialManager.__instance is not None:

            self.logger.error("Attempted to recreate an instance of a SerialManager - should use Instance()")
            raise Exception(
                "Attempted to instantiate a new SerialManager, but only one instance is"
                " allowed.  Use the Instance() method instead")
        else:
            self.logger.debug("SerialManager __init__")
            SerialManager.__instance = self

        # create a database object
        self.__data = DatabaseServer()

    @classmethod
    def Instance(cls):
        """
        Returns a reference to a single SerialManager instance
        """
        cls.logger.debug("SerialManager Instance called")
        if cls.__instance is None:
            return SerialManager()
        else:
            return cls.__instance

    def start(self):
        """
        Starts listening on the serial ports and polling for updates every SerialUpdatePeriod seconds
        """

        # start a thread for listening to the serial ports
        self.__stop_event = threading.Event()
        self.__listen_thread = threading.Thread(target=self.__listen_serial, args=[self.__stop_event])
        self.__listen_thread.daemon = True
        self.__listen_thread.start()
        self.logger.debug("Started serial listening thread: %s" % self.__listen_thread.name)

        # Start a thread for polling serial for updates
        self.__serial_thread = threading.Thread(target=self.__poll_serial, args=[self.__stop_event])
        self.__serial_thread.daemon = True
        self.__serial_thread.start()
        self.logger.debug("Started serial polling thread: %s" % self.__serial_thread.name)

        # log about serial listening starting
        self.logger.info("Commenced listening and polling serial ports for updates")


    def __poll_serial(self, stop_event):
        """
        A thread which periodically polls a serial connection until a stop_event is received
        """
        while not stop_event.set():
            with self.__queue_lock:
                # todo - this is fake :/ actually need to send a message to the boards requesting an update
                self.__data.queue(generate_tcp_server_fixtures())

            time.sleep(SerialUpdatePeriod / 4)  # TODO currently 0.25 of serial period to generate lots of data
                                                # TODO remove the " / 4" later

    def __listen_serial(self, stop_event):
        """
        A threaded function that listens on a serial port and queues any received messages into the inbox
        """
        while not stop_event.set():
            # todo - something useful
            pass
