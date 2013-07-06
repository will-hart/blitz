__author__ = 'Will Hart'

import logging
import threading
import time

from redis import ConnectionError

from blitz.constants import SerialUpdatePeriod
from blitz.data.database import DatabaseServer
from blitz.io.signals import logging_started, logging_stopped
from blitz.utilities import generate_tcp_server_fixtures


class SerialManager(object):
    """
    Manages serial (RS232, SPI or I2C) communications with expansion
    boards.  It has both a monitoring loop and an "outbox" which it
    uses for sending information.
    """

    __instance = None
    __data = None
    __serial_thread = None
    __listen_thread = None

    logger = logging.getLogger(__name__)

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
        try:
            self.__data = DatabaseServer()
        except ConnectionError as e:
            self.logger.critical("ConnectionError when attempting to start the DatabaseServer!")
            self.logger.critical(e)
        # register to signals
        logging_started.connect(self.start)
        logging_stopped.connect(self.stop)

    def start(self, signal_args):
        """
        Starts listening on the serial ports and polling for updates every SerialUpdatePeriod seconds
        """

        # enter a new session
        session_id = self.__data.start_session()

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
        self.logger.info("Commenced logging session %s" % session_id)

    def stop(self, signal_args):
        """Stops logging threads"""

        self.logger.debug("Received signal to stop logging")

        # end the new session
        self.__data.stop_session()

        self.__stop_event.set()
        self.__listen_thread.join()
        self.logger.debug("Stopped listening for new serial messages")
        self.__serial_thread.join()
        self.logger.info("All serial threads have now stopped")

    def __poll_serial(self, stop_event):
        """
        A thread which periodically polls a serial connection until a stop_event is received
        """
        while not stop_event.is_set():
            # todo - this is fake :/ actually need to send a message to the boards requesting an update
            self.__data.queue(generate_tcp_server_fixtures())

            time.sleep(SerialUpdatePeriod / 4)  # TODO currently 0.25 of serial period to generate lots of data
                                                # TODO remove the " / 4" later

        self.logger.debug("Exited poll serial thread")

    def __listen_serial(self, stop_event):
        """
        A threaded function that listens on a serial port and queues any received messages into the inbox
        """
        while not stop_event.is_set():
            # todo - something useful
            time.sleep(0.5)

        self.logger.debug("Exited listen serial thread")
