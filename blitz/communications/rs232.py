__author__ = 'Will Hart'


import logging
import os
from redis import ConnectionError
import serial
from serial.tools.list_ports import comports
import time
import threading

from blitz import constants
from blitz.communications.signals import board_command_received, logging_started, logging_stopped
from blitz.constants import CommunicationCodes, SerialUpdatePeriod, SerialCommands
from blitz.data.database import DatabaseServer
from blitz.plugins import Plugin, PluginMount


class ExpansionBoardNotFound(BaseException):
    """
    An error thrown when an the SerialManager is requested to communicate with a board that it doesn't
    have in its communications dictionary
    """
    pass


class SerialManager(Plugin):
    """
    Manages serial (eventually RS232, SPI or I2C) communications with
    expansion boards.  It has both a monitoring loop and an "outbox"
    which it uses for sending information.
    """

    __instance = None
    do_not_register = False
    database = None
    serial_mapping = None
    __serial_thread = None
    __stop_event = None

    logger = logging.getLogger(__name__)

    @classmethod
    def instance(cls):
        """
        Gets the instance of the SerialManager created during plugin loading
        """
        if not cls.__instance:
            # get from the plugin list
            cls.__instance = PluginMount.get_plugin(type(SerialManager))

        return cls.__instance

    def __init__(self, description="Serial Manager Board"):
        """
        Follows a singleton pattern and prevents instantiation of more than one Serial Manager.

        :returns: Nothing
        """
        try:
            if SerialManager:
                self.logger.critical("Attempted to instantiate a SerialManager directly rather than as a plugin")
                raise RuntimeError("Attempted to instantiate a SerialManager directly rather than as a plugin")
        except NameError:
            pass

        self.description = description
        Plugin.__init__(self, description)

        # create a database object
        try:
            self.database = DatabaseServer()
        except ConnectionError as e:
            self.logger.critical("ConnectionError when attempting to start the DatabaseServer!")
            self.logger.critical(e)

        # work out which serial ports are connected
        self.get_available_ports()

    def register_signals(self):
        # register signals
        logging_started.connect(self.start)
        logging_stopped.connect(self.stop)
        board_command_received.connect(self.handle_board_command)

    def get_available_ports(self):
        """
        Generates a list of available serial ports, mapping their ID to
        the COM* or /dev/tty* reference.  Adapted from http://stackoverflow.com/a/14224477/233608

        :returns: Nothing
        """
        self.logger.info("Scanning for available serial ports")
        self.serial_mapping = {}
        ports = []

        # Windows
        if os.name == 'nt':
            self.logger.debug("Performing Windows scan")

            # scan for available ports
            for i in range(256):
                try:
                    portname = "COM%s" % (i + 1)
                    s = self.open_serial_connection(portname)
                    s.close()
                    ports.append(portname)

                except serial.SerialException:
                    pass
        else:
            # Mac / Linux
            self.logger.debug("Performing Mac/Linux scan for expansion boards on serial ports")
            for port in comports():
                ports.append(port[0])

        for port in ports:
            ser = self.open_serial_connection(port)
            board_id = self.send_id_request(ser)
            if board_id is not None:
                self.logger.info("Found board ID %s at %s" % (board_id, port))
                self.serial_mapping[hex(board_id)[2:].zfill(2)] = ser
            else:
                ser.close()

    @staticmethod
    def open_serial_connection(port_name, baud_rate=57600, read_timeout=3):
        """
        Creates a serial port connection, opens it and returns it.  Note if you are using USB serial and
        an Arduino you may need to put a resistor between 5V or 3.3V and the RESET pin to prevent auto reset.
        This should only be required during development using a PC. Check the interwebs for the correct
        resistance value (this is a known issue)

        :param port_name: the name of the port to open (for instance COM3)
        :param baud_rate: the baud rate of the serial connection (default 57600)
        :param read_timeout: the timeout to use for reading from ports (default 3 seconds)

        :return: An open serial port object
        """
        return serial.Serial(port=port_name, baudrate=baud_rate, timeout=read_timeout)

    def reset_expansion_board(self, board_id):
        """
        Resets the (Arduino Based) expansion board on the given port by toggling the DTR line.
        Only works for Arduino based expansion boards

        :param board_id: the serial port to send the reset command to
        """
        s = self.serial_mapping[board_id]

        if s is not None:
            s.setDTR(False)
            time.sleep(0.03)
            s.setDTR(True)
        else:
            self.logger.warn("Attempted to reset unknown board ID %s" % board_id)

    def send_id_request(self, port):
        """
        Requests an ID from the serial port name and returns it.
        If no ID is found, return None

        :param port: the serial port handle to read/write from

        :returns: A two digit hex board ID, or None if no ID was found
        """
        board_id = None

        # clear out any junk in the board's serial buffer and ignore the response
        port.write('\n')
        port.readline()

        # send the ID request
        port.write('00' + SerialCommands['ID'] + '\n')
        serial_buffer = port.readline()

        # check if a valid id was returned
        if len(serial_buffer) > 2:
            board_id = int(serial_buffer[0:2], 16)
            self.logger.debug("Received serial ID %s from port %s" % (board_id, port.port))

        return board_id

    def receive_serial_data(self, board_id):
        """
        Requests a transmission from the specified board and
        saves the returned data to the database

        :param board_id: the ID of the board in hex form, (e.g. "08" for board with ID 8)

        :returns: Nothing
        """
        port = self.serial_mapping[board_id]
        self.logger.debug("Sending '%s' on '%s' for board status update" % (
            board_id + SerialCommands['TRANSMIT'], port.port))

        # send the transmit request
        port.write(board_id + SerialCommands['TRANSMIT'] + '\n')

        # readlines until no more lines left (will read for the timeout period)
        lines = port.readlines()

        for line in lines:
            line = line.replace('\n', '').replace('\r', '')
            line_size = len(line)
            if line_size < 4:
                self.logger.debug("Received short message (%s) from board %s, ignoring" % (line, board_id))

            elif line_size == 4:
                # a short message
                command = line[2:]
                if command == SerialCommands['ACK']:
                    self.logger.debug("Received serial ACK from board %s" % board_id)
                    break  # all done, ignore the rest

            else:
                # a data message, save it for later
                self.logger.debug("Received serial data from board %s: %s" % (board_id, line))
                self.database.queue(line)

        self.logger.debug("Finished receiving data from board %s" % board_id)

    def send_command_with_ack(self, command, board_id):
        """
        Sends the given command over the serial port and checks for
        an ACK response.  Returns None if the ACK was received, and the
        received message otherwise

        :param command: the string command to send over the serial port, from the SerialCommands constant
        :param board_id: the ID of the board in hex form, (e.g. "08" for board with ID 8)

        :raises ExpansionBoardNotFound: when a message is sent to an expansion board which doesn't exist

        :returns: the board response if an error was received, or None if ACK was received
        """

        try:
            port = self.serial_mapping[board_id]
        except KeyError:
            raise ExpansionBoardNotFound("Unable to find board %s - it doesn't appear to be connected" % board_id)

        # clear existing
        port.write('\n')
        port.readline()

        # set up the command
        command = board_id + command

        # if it is a command with payload, pad it out to the full message length
        if len(command) > 4:
            # TODO: This length should probably be without the -1!?
            command = command.ljust(constants.MESSAGE_BYTE_LENGTH - 1, "0") + "\n"

        # write the command
        port.write(command)

        # read the response
        serial_buffer = port.readline().replace('\n', '').replace('\r', '')

        # TODO: properly handle errors
        self.logger.debug("Sent {0} on {1}, received \"{2}\"".format(
            board_id + command.replace('/n', ''), port.port, serial_buffer))

        if len(serial_buffer) != 4 or serial_buffer[2:] != SerialCommands['ACK']:
            return serial_buffer

        return None

    def start(self, tcp):
        """
        Starts listening on the serial ports and polling for updates every SerialUpdatePeriod seconds

        :param tcp: the TCP connection to use for communications

        :returns: Nothing
        """

        if self.database is None:
            # unable to start a session if no local database is present
            tcp.send(CommunicationCodes.composite(CommunicationCodes.Error, 3))
            return

        # enter a new session
        session_id = self.database.start_session()

        # send a start signal to all boards
        for k in self.serial_mapping.keys():
            success = self.send_command_with_ack(SerialCommands['START'], k)

            # log errors for now
            if not success is None:
                self.logger.warn("Received '%s' instead of ACK from board ID %s on START" % (success, k))
            else:
                self.logger.debug("Board %s has started logging" % k)

        # Start a thread for polling serial for updates
        self.__stop_event = threading.Event()
        self.__serial_thread = threading.Thread(target=self.__poll_serial, args=[self.__stop_event])
        self.__serial_thread.daemon = True
        self.__serial_thread.start()
        self.logger.debug("Started serial polling thread: %s" % self.__serial_thread.name)

        # log about serial listening starting
        self.logger.info("Commenced logging session %s" % session_id)

    def stop(self, signal_args):
        """
        Stops logging data and sends a STOP request to all boards

        :param signal_args: the arguments provided by the blinker signal (unused)

        :returns: Nothing
        """

        self.logger.debug("Received signal to stop logging")

        if self.__stop_event is not None:
            self.__stop_event.set()
            self.__serial_thread.join()
            self.logger.info("Serial polling stopped")

            # send a stop signal to all boards
            for k in self.serial_mapping.keys():

                # clear out the serial buffer
                self.receive_serial_data(k)

                # then stop the board
                success = self.send_command_with_ack(SerialCommands['STOP'], k)

                # log errors for now instead of doing something about them
                if not success is None:
                    self.logger.warning("Received '%s' instead of ACK from board ID %s on STOP" % (success, k))
                else:
                    self.logger.debug("Board %s has stopped logging" % k)

        # end the new session
        if self.database is not None:
            self.database.stop_session()
            self.logger.debug("Database server session stopped")

    def handle_board_command(self, signal_args):
        """
        Listens for board commands and distributes them to the correct board.

        :param signal_args: the arguments received from the blinker signal. In the form ['BOARD ID', 'ARGS', ...]
        """

        self.logger.debug("Handling board command with arguments {0}".format(signal_args))

        # get the command components and send via serial
        command = ''.join([x for x in signal_args[1:]])
        response = self.send_command_with_ack(command, signal_args[0])

        if response:
            self.logger.warning("Received unexpected response {0} when sending command {1} to board {2}. ".format(
                response, command, signal_args[0]))

    def __poll_serial(self, stop_event):
        """
        A thread which periodically polls a serial connection until a stop_event is received

        :param stop_event: the threading Event which triggers stopping serial listening

        :returns: Nothing
        """

        self.logger.debug("Commencing Serial polling loop")

        while not stop_event.is_set():
            # enumerate each port
            for k in self.serial_mapping.keys():
                self.receive_serial_data(k)

            time.sleep(SerialUpdatePeriod)

        self.logger.debug("Exited poll serial thread")

    def __del__(self):
        """
        Destroys the SerialManager and closes all open ports
        """
        self.logger.warning("Shutting down SerialManager")

        for k in self.serial_mapping.keys():
            try:
                self.serial_mapping[k].close()
                self.logger.info("Closed connection to board ID %s" % k)
            except:
                pass
