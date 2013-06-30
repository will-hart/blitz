__author__ = 'Will Hart'

import datetime
import logging

from bitstring import BitArray
from construct import Struct, UBInt8, UBInt16, UBInt32, BitStruct, BitField, Flag, FieldError

from blitz.io.signals import data_line_received, data_line_processed, registering_boards


class BoardManager(object):
    """
    A BoardManager registers expansion boards and handles parsing
    of raw messages and insertion into the database
    """

    boards = {}
    logger = logging.getLogger(__name__)

    def __init__(self, database):
        """
        Register boards by ID
        """

        # save a reference to the database
        self.data = database

        # send the signal to register boards
        registering_boards.send(self)

    def register_board(self, board_id, board):
        """
        Register a board against the given ID, throwing an error if
        the board is already registered
        """
        if board_id in self.boards.keys():
            self.logger.error("Failed to register board [%s: %s]" % (board_id, board.description))
            raise Exception("Attempted to register a board against an existing ID: %s" % board_id)

        self.logger.info("Registered expansion board [%s: %s]" % (board_id, board.description))
        self.boards[board_id] = board

    def parse_message(self, message, board_id, session_id=None):
        """
        Gets a variable dictionary from a board and save to database
        :rtype : bool
        :return: True if successfully parsed, False if unable to parse
        :param message: The raw message to parse
        :param board_id: The id of the board to parse the message
        :param session_id: The session ID of the message (ignore if getting cached variables)
        """

        try:
            board = self.boards[board_id]
        except KeyError:
            self.logger.debug("Ignoring message (%s) for unknown board id - %s" % (message, board_id))
            return False

        # use the board to parse the message
        board.parse_message(message)
        result = board.get_variables()

        # get session metadata
        timeLogged = datetime.datetime.from_timestamp(board.get_timestamp())

        # write the variables to the database
        for key in result.keys():
            category_id = self.data.get_or_create_category(key)
            if session_id:
                # adding a reading
                self.data.add_reading(session_id, timeLogged, category_id, result[key])
            else:
                # adding to cache
                self.data.add_cache(timeLogged, category_id, result[key])

        return True


class BaseExpansionBoard(object):
    """
    A class that all client side expansion boards MUST inherit.  In addition,
    boards which are derived from BaseExpansionBoard must call the constructor
    of this class in their derived class using "super"

    This provides basic functionality such as parsing of raw logger messages
    """

    def __init__(self):
        """
        Initialises the Expansion Board
        """
        self._mapping_struct = Struct("mapping",
                                      UBInt8("sender"),
                                      BitStruct("meta",
                                                BitField("type", 3),
                                                Flag("flag_one"),
                                                Flag("flag_two"),
                                                Flag("flag_three"),
                                                Flag("flag_four"),
                                                Flag("flag_five")),
                                      UBInt16("timestamp"),
                                      UBInt32("payload"))
        self._generated = None

        # ensure this board has an ID (should be unique, 0-255)
        self.identify_board()

        # subscribe to the registering_boards signal
        registering_boards.connect(self.register_board)

    def parse_message(self, raw_message):
        """
        Takes a raw binary message received from an expansion board and breaks
        it up into parts as described in section 4 of TS0002.

        This method SHOULD NOT be overridden in derived classes.  Derived classes
        should implement the get_variables function
        """

        # raise the pre-processing event
        data_line_received.send(raw_message)

        # parse the message
        try:
            self._generated = self._mapping_struct.parse(raw_message)
        except FieldError:
            raise Exception(
                "Unable to parse message [%s]- expected 8 bytes, found %s" % (
                    raw_message, len(raw_message))
            )

        # get the payload into a bit_array
        self._payload_array = BitArray(hex(self._generated.payload))

        # create a flags array
        self._flags = [
            self._generated.meta.flag_one,
            self._generated.meta.flag_two,
            self._generated.meta.flag_three,
            self._generated.meta.flag_four,
            self._generated.meta.flag_five
        ]

        # raise the finished event
        data_line_processed.send(raw_message)

    def register_board(self, manager):
        """
        Registers this board (by ID) with the board manager.  This method SHOULD NOT
        be overridden by derived classes
        """
        manager.register_board(self.id, self)

    def get_number(self, start_bit, length):
        """
        Get a number from the payload, breaking out bits between 'start_bit' and 'length'.
        Note that the bits are 1 indexed - e.g. the first bit is bit #1
        This method SHOULD NOT be overridden by derived classes
        """
        start = start_bit - 1
        end = start + length
        return self._payload_array[start:end].int

    def get_type(self):
        """
        Gets the type of message (3 bit identifier as an integer)
        This method SHOULD NOT be overridden by derived classes
        """
        return self._generated.meta.type

    def get_flag(self, bit_number):
        """
        Returns the flag defined at the given bit number.
        This method SHOULD NOT be overridden by derived classes
        """
        if bit_number > len(self._flags) or bit_number < 0:
            raise Exception("Invalid flag number %s, should be between 0 and 4 (inclusive)" % bit_number)
        return self._flags[bit_number]

    def get_raw_payload(self):
        """
        Get the raw payload (an unsigned, big endian, 32 bit number)
        This method SHOULD NOT be overridden by derived classes
        """
        return self._generated.payload

    def get_timestamp(self):
        """
        Returns the timestamp (UNIX TIMESTAMP format) from the message
        This method SHOULD NOT be overridden by derived classes
        """
        return self._generated.timestamp

    def identify_board(self):
        """
        Sets the ID of this board (0-255).
        This method MUST be overriden by derived classes
        """
        self.id = -1
        self.description = "Base Expansion Board"

    def get_variables(self):
        """
        Queries the split up binary data generated by self.parse_message and
        creates a dictionary of "variable": "value" pairs.
        This method MUST be overridden by derived classes
        """
        return {}


class BlitzBasicExpansionBoard(BaseExpansionBoard):
    """
    A basic expansion board with three 10bit ADCs
    """

    def identify_board(self):
        self.id = 1
        self.description = "Blitz Basic Expansion Board"

    def get_variables(self):
        return {
            "adc_channel_one": self.get_number(1, 10),
            "adc_channel_two": self.get_number(11, 10),
            "adc_channel_three": self.get_number(21, 10)
        }
