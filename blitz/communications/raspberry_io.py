__author__ = 'Will Hart'

# we should only import this Raspberry Pi manager if RPi.GPIO is installed
try:
    import RPi.GPIO as GPIO
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

            self.logger.debug("Configuration RaspberryPi IO Ports")

            # set up the board numbering mode and put pins in the correct mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(4, GPIO.IN)
            GPIO.setup(17, GPIO.IN)
            GPIO.setup(18, GPIO.IN)
            GPIO.setup(21, GPIO.IN)
            GPIO.setup(22, GPIO.IN)
            GPIO.setup(23, GPIO.IN)
            GPIO.setup(24, GPIO.IN)
            GPIO.setup(25, GPIO.IN)
            GPIO.setup(30, GPIO.IN)
            GPIO.setup(31, GPIO.IN)

            self.logger.debug("Starting Raspberry Pi GPIO polling")
            while not stop_event.is_set():

                # read in the pins
                results = [
                    GPIO.setup(4, GPIO.IN),
                    GPIO.setup(17, GPIO.IN),
                    GPIO.setup(18, GPIO.IN),
                    GPIO.setup(21, GPIO.IN),
                    GPIO.setup(22, GPIO.IN),
                    GPIO.setup(23, GPIO.IN),
                    GPIO.setup(24, GPIO.IN),
                    GPIO.setup(25, GPIO.IN)
                ]

                # build up a single object
                result = 0
                for r in results:
                    result = (result | r) << 1

                # build the base message
                delta_t = (datetime.datetime.now() - self.__logging_start).total_seconds() * 1000.0
                formatted_result = "03A0" + hex(int(delta_t))[2:].rjust(8, '0').upper()
                formatted_result += hex(int(result))[2:].rjust(2, '0').upper()

                # store the result
                self.__data.queue(formatted_result)

                # sleepy time
                time.sleep(1.0 / self.SAMPLE_FREQUENCY)

            # terminate the context before exiting
            self.logger.debug("Raspberry Pi GPIO polling terminated")

        def start_logging(self, args):
            """
            Stores the current time when data logging commences so the correct timestamp can be provided to messages
            """
            self.__logging_start = datetime.datetime.now()
            self.__run_thread(self.run_client)


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
