__author__ = 'Will Hart'

import logging

from bitstring import BitArray

from blitz.constants import BOARD_MESSAGE_MAPPING, PAYLOAD_LENGTH, MESSAGE_BYTE_LENGTH
from blitz.data.models import Reading
from blitz.communications.signals import data_line_received, data_line_processed, registering_boards, \
    logging_started, logging_stopped, board_command_received
from blitz.communications.netscanner_manager import NetScannerManager
from blitz.communications.rs232 import SerialManager
from blitz.plugins import Plugin
from blitz.utilities import blitz_timestamp


class BoardManager(object):
    """
    A BoardManager registers expansion boards and handles parsing
    of raw messages and insertion into the database
    """

    logger = logging.getLogger(__name__)

    def __init__(self, database):
        """
        Register boards by ID
        """

        # save a reference to the database
        self.data = database
        self.boards = {}

        # send the signal to register boards
        registering_boards.send(self)

        # connect the data line received message
        data_line_received.connect(self.parse_session_message)
        board_command_received.connect(self.handle_board_command)

    def handle_board_command(self, command):
        """
        Processes a board command received via TCP and sends the required message to an expansion board.

        The received command should correspond toa serial communications command, for instance to set a
        motor position on a board with ID #9, the client would send::

            098500000A

        In this case, `09` is the board ID, `85` is the "set motor position" command, `0000` is the
        timestamp section of the message and `0A` is the position to set.
        """

        board_id = int(command[0:2], 16)
        command = command[2:]
        board = None

        try:
            board = self.boards[board_id]
        except KeyError:
            self.logger.warning("Ignoring command (%s) for unknown board id - %s" % (command, board_id))
            return

        board.send_command(command)

    def register_board(self, board_id, board):
        """
        Register a board against the given ID, throwing an error if
        the board is already registered
        """

        if board_id in self.boards.keys():
            self.logger.error("Error registering duplicate board [%s: %s]" % (board_id, board.description))
            raise Exception("Attempted to register a board against an existing ID: %s" % board_id)

        self.logger.info("Registered expansion board [%s: %s]" % (board_id, board.description))
        self.boards[board_id] = board

    def parse_session_message(self, message_tuple):
        """
        Passes the received message to the board manager message parser with the appropriate session id
        """

        messages, session_id = message_tuple
        decoded_vars = []

        for msg in messages:
            decoded_vars += self.parse_message(msg, session_id=session_id)

        # perform a single database transaction
        self.data.add_many(decoded_vars)

        # work out if the session is fully downloaded
        self.data.update_session_availability(session_id)

    def parse_message(self, message, session_id=None, board_id=None):
        """
        Gets a variable dictionary from a board and save to database
        :param message: The raw message to parse
        :param session_id: The session ID of the message (ignore if getting cached variables)
        :param board_id: The id of the board to parse the message
        :returns: a list of variables added to the cache or data store
        """

        readings = []

        if board_id is None:
            board_id = int(message[0:2], 16)

        try:
            board = self.boards[board_id]
        except KeyError:
            self.logger.warning("Ignoring message (%s) for unknown board id - %s" % (message, board_id))
            return []

        # use the board to parse the message
        board.parse_message(message)
        result = board.get_variables()

        # get session metadata
        if session_id:
            # TODO add timestamp to session start time
            timeLogged = - board["timestamp"]
        else:
            timeLogged = blitz_timestamp()  # for cached just pretend its now

        # write the variables to the database
        for key in result.keys():
            category_id = self.data.get_or_create_category(key)
            if session_id:
                # adding a reading
                readings.append(
                    Reading(sessionId=session_id, timeLogged=timeLogged, categoryId=category_id, value=result[key]))
            else:
                # adding to cache
                cached_item = self.data.add_cache(timeLogged, category_id, result[key])
                readings.append({
                    'categoryId': cached_item.categoryId,
                    #'timeLogged': dt.datetime.fromtimestamp(cached_item.timeLogged / 1000),  # convert unix to python dates
                    'timeLogged': cached_item.timeLogged / 1000,
                    'value': float(cached_item.value)
                })

        return readings


class BaseExpansionBoard(Plugin):
    """
    A class that all client side expansion boards MUST inherit.  In addition,
    boards which are derived from BaseExpansionBoard must call the constructor
    of this class in their derived class using "super"

    This provides basic functionality such as parsing of raw logger messages
    """

    logger = logging.getLogger(__name__)
    do_not_register = True  # prevent registration of this board in the plugins list

    def __init__(self, description="Base Expansion Board"):
        """
        Initialises the Expansion Board
        """
        Plugin.__init__(self, description)
        self.description = description
        self.id = -1
        self.__message = None
        self.__attributes = {}
        self.__mapping = BOARD_MESSAGE_MAPPING
        self._payload_array = None

    def __getitem__(self, item):
        """Override get item to provide access to attributes"""

        # handle board descriptive attributes
        # this is not necessary but provides a common interface
        if item == "id":
            return self.id
        elif item == "description":
            return self.description

        # otherwise return an item from the __attributes dictionary
        if item in self.__attributes.keys():
            return self.__attributes[item]
        else:
            raise KeyError("Attempted to get variable from the board which doesn't exist: %s" % item)

    def __setitem__(self, key, value):
        """Override set item to provide access to attributes"""
        self.__attributes[key] = value

    def parse_message(self, raw_message):
        """
        Takes a raw binary message received from an expansion board and breaks
        it up into parts as described in section 4 of TS0002.

        This method SHOULD NOT be overridden in derived classes.  Derived classes
        should implement the get_variables function
        """

        # parse the message
        if len(raw_message) < MESSAGE_BYTE_LENGTH:
            raise Exception(
                "Unable to parse message [%s]- expected 28 bytes, found %s" % (
                    raw_message, len(raw_message))
            )

        self.__message = BitArray(hex=raw_message)

        # parse all the variables to match the mapping
        for key in self.__mapping.keys():
            if "end" in self.__mapping[key]:
                if self.__mapping[key]["end"] == -1:
                    self[key] = self.__message[self.__mapping[key]["start"]:].uint
                else:
                    self[key] = self.__message[self.__mapping[key]["start"]:self.__mapping[key]["end"]].uint
            else:
                self[key] = self.__message[self.__mapping[key]["start"]]

        # get the payload into a bit_array
        # TODO Extended messages using PAYLOAD_LENGTH + (len(raw_message) - 28) * 4)
        self._payload_array = BitArray(uint=self["payload"], length=PAYLOAD_LENGTH)

        # create a flags array
        self['flags'] = [
            self["flag1"],
            self["flag2"],
            self["flag3"],
            self["flag4"],
            self["flag5"],
        ]

        # raise the finished event
        data_line_processed.send(self)

    def register_board(self, manager):
        """
        Registers this board (by ID) with the board manager.  This method SHOULD NOT
        be overridden by derived classes
        """
        manager.register_board(self['id'], self)

    def get_number(self, start_bit, length):
        """
        Get a number from the payload, breaking out bits between 'start_bit' and 'length'.
        Note that the bits are 0 indexed - e.g. the first bit is bit #0, the second is #1, etc.
        This method SHOULD NOT be overridden by derived classes
        """
        start = start_bit
        end = start + length
        return self._payload_array[start:end].uint

    def get_flag(self, flag_number):
        """
        Returns the flag defined at the given bit number.
        This method SHOULD NOT be overridden by derived classes
        """
        if flag_number > len(self['flags']) or flag_number < 0:
            raise Exception("Invalid flag number %s, should be between 0 and 4 (inclusive)" % flag_number)
        return self['flags'][flag_number]

    def get_raw_payload(self):
        """
        Get the raw payload (an unsigned, big endian, 32 bit number)
        This method SHOULD NOT be overridden by derived classes
        """
        return self['payload']

    def get_variables(self):
        """
        Queries the split up binary data generated by self.parse_message and
        creates a dictionary of "variable": "value" pairs.
        This method MUST be overridden by derived classes
        """
        return {}

    def send_command(self, command):
        """
        Sends a command using the preferred method of the board.  Can be overridden in inherited classes
        to provide behaviour other than the default RS232 transmission
        """
        result = SerialManager.Instance().send_command_with_ack(command, self.id)

        if result == None:
            return

        self.logger.warning("Board unable to process command (%s) received response (%s)" %(command, result))


class BlitzBasicExpansionBoard(BaseExpansionBoard):
    """
    A basic expansion board with three 10bit ADCs
    """

    def __init__(self, description="Blitz Basic Expansion Board"):
        """load the correct description for the board"""
        BaseExpansionBoard.__init__(self, description)
        self.do_not_register = False
        self.id = 8
        self.description = description

    def register_signals(self):
        """Connect to the board loading signal"""
        self.logger.debug(
            "Board [%s:%s] now listening for registering_boards signal" % (self['id'], self['description']))
        registering_boards.connect(self.register_board)

    def get_variables(self):
        #print self._payload_array.hex
        return {
            "adc_channel_one": self.get_number(0, 12),
            "adc_channel_two": self.get_number(12, 12),
            "adc_channel_three": self.get_number(24, 12),
            "adc_channel_four": self.get_number(36, 12),
            "adc_channel_five": self.get_number(48, 12)
        }


class MotorExpansionBoard(BaseExpansionBoard):
    """
    A simple expansion board which allows setting a motor position or speed
    and returns three values as 16 bit integers:

     1. the current ADC value
     2. the current measured position / speed
     3. the set position / speed
    """

    def __init__(self, description="Motor Expansion Board"):
        BaseExpansionBoard.__init__(self, description)
        self.do_not_register = False
        self.id = 9
        self.description = description

    def register_signals(self):
        """Connect to the board loading signal"""
        self.logger.debug(
            "Board [%s:%s] now listening for registering_boards signal" % (self['id'], self['description']))
        registering_boards.connect(self.register_board)

    def get_variables(self):
        #print self._payload_array.hex
        return {
            "raw_adc": self.get_number(0, 16),
            "motor_value": self.get_number(16, 16),
            "set_point": self.get_number(32, 16)
        }


class NetScannerEthernetBoard(BaseExpansionBoard):
    """
    An ethernet based expansion board for communicating with two NetScanner 9116 devices
    connected to a NetScanner 9IFC.  The protocol is available from the NetScanner manuals
    """

    def __init__(self, description="NetScanner Ethernet Interface Board"):
        """load the correct description for the board"""
        BaseExpansionBoard.__init__(self, description)
        self.do_not_register = False
        self.id = 10
        self.description = description
        self.__net_scanner = None

    def register_signals(self):
        # signal to register the board
        registering_boards.connect(self.register_board)
        self.logger.debug(
            "Board [%s:%s] now listening for registering_boards signal" % (self['id'], self['description']))

        # signal to start logging
        logging_started.connect(self.start_polling)
        self.logger.debug(
            "Board [%s:%s] now listening for logging_started signal" % (self['id'], self['description']))

        logging_stopped.connect(self.stop_polling)
        self.logger.debug(
            "Board [%s:%s] now listening for logging_stopped signal" % (self['id'], self['description']))

    def start_polling(self):
        """
        Communicates with a NetScanner 9116 via TCP, telling it to
        start recording
        """
        # TODO implement correct IP/Port
        self.__net_scanner = NetScannerManager("192.168.1.1", "9000")

    def stop_polling(self):
        """
        Stops polling a NetScanner board
        """
        self.__net_scanner.stop_client()

    def get_variables(self):
        results = self.__net_scanner.get_channels()
        return dict([("Channel %s" % x[0], x[1]) for x in enumerate(results)])
