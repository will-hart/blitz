__author__ = 'Will Hart'

# we should only import this Raspberry Pi manager if RPi.GPIO is installed
try:
    import RPi.GPIO as gpio
except ImportError:

    pass
else:
    import datetime
    import logging
    import threading
    import time

    from blitz.communications.signals import logging_started, logging_stopped


    class RPIOManager(object):
        """
        Read from the Raspberry Pi IO pins
        """

        SAMPLE_FREQUENCY = 5

        logger = logging.getLogger(__name__)

        def __init__(self, database):
            """
            Initialises the Raspberry Pi GPIO pins for IO

            :param database: The database to use to save serial data
            """

            self.__data = database
            self.board_id = 3
            self.__stop_event = threading.Event()
            self.__run_thread(self.run_client)
            self.__thread = None
            self.__logging_start = datetime.datetime.now()

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

            self.logger.debug("Starting Raspberry Pi GPIO polling")

            while not stop_event.is_set():
                time.sleep(1.0 / self.SAMPLE_FREQUENCY)

            # terminate the context before exiting
            self.logger.debug("Raspberry Pi GPIO polling terminated")

        def start_logging(self, args):
            """
            Stores the current time when data logging commences so the correct timestamp can be provided to messages
            """
            self.__logging_start = datetime.datetime.now()
            self.__run_thread()


        def receive_message(self, channels):
            """
            Receives and handles data retrieved from the Raspberry Pi GPIO

            :param message: the message that was received
            """
            pass

        def stop_client(self):
            """
            Stops a client from polling
            """
            self.__stop_event.set()
            self.__thread.join()
            self.__thread = None
            self.logger.debug("Raspberry Pi GPIO thread stopped")
