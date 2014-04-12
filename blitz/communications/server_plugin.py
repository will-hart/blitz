__author__ = 'Will Hart'

# we should only import this Raspberry Pi manager if RPi.GPIO is installed

import datetime
import logging
import threading
import time

from blitz.communications.signals import logging_started, logging_stopped


class ServerPluginBase(object):
    """
    A base class for running server plugins such as the NetScanner and Raspberry Pi IO
    """

    SAMPLE_FREQUENCY = 5

    logger = logging.getLogger(__name__)

    def __init__(self, database):
        """
        Initialises the Raspberry Pi GPIO pins for IO

        :param database: The database to use to save serial data
        """

        self.__data = database
        self.__stop_event = threading.Event()
        self.__run_thread(self.run_client)
        self.__thread = None

        logging_started.connect(self.start_logging)
        logging_stopped.connect(self.stop_client)

    def __run_thread(self, thread_target):

        if self.__thread:
            self.logger.debug("Closing existing Raspberry Pi polling thread")
            self.__stop_event.set()
            self.__thread.join()

        self.__thread = threading.Thread(target=thread_target, args=[self.__stop_event])
        self.__thread.daemon = True
        self.__thread.start()

    def run_client(self, stop_event):
        raise NotImplementedError("Base Server Plugin 'run_client' is not implemented")

    def start_logging(self, args):
        """
        Stores the current time when data logging commences so the correct timestamp can be provided to messages
        """
        self.__run_thread(self.run_client)

    def stop_client(self):
        """
        Stops a client from polling
        """
        self.__stop_event.set()
        self.__thread.join()
        self.__thread = None
