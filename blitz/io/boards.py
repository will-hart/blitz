__author__ = 'Will Hart'

import datetime
import logging

from bitstring import BitArray

from blitz.constants import BOARD_MESSAGE_MAPPING, PAYLOAD_LENGTH, MESSAGE_BYTE_LENGTH
from blitz.io.signals import data_line_received, data_line_processed, registering_boards
from blitz.plugins import Plugin


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


class BaseExpansionBoard(Plugin):
    """
    A class that all client side expansion boards MUST inherit.  In addition,
    boards which are derived from BaseExpansionBoard must call the constructor
    of this class in their derived class using "super"

    This provides basic functionality such as parsing of raw logger messages
    """

    logger = logging.getLogger(__name__)
    board_id = -1
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

        # raise the pre-processing event
        data_line_received.send(raw_message)

        # parse the message
        if len(raw_message) < MESSAGE_BYTE_LENGTH:
            raise Exception(
                "Unable to parse message [%s]- expected 28 bytes, found %s" % (
                    raw_message, len(raw_message))
            )

        self.__message = BitArray(hex="0x" + raw_message)

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
        self._payload_array = BitArray(uint=self["payload"], length=PAYLOAD_LENGTH + (len(raw_message)- 28) * 4)

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


class BlitzBasicExpansionBoard(BaseExpansionBoard):
    """
    A basic expansion board with three 10bit ADCs
    """

    def __init__(self, description="Blitz Basic Expansion Board"):
        """load the correct description for the board"""
        BaseExpansionBoard.__init__(self, description)
        self.do_not_register = False
        self.id = 1
        self.description = description

    def register_signals(self):
        """Connect to the board loading signal"""
        self.logger.debug(
            "Board [%s:%s] now listening for registering_boards signal" % (self['id'], self['description']))
        registering_boards.connect(self.register_board)

    def get_variables(self):
        return {
            "adc_channel_one": self.get_number(0, 12),
            "adc_channel_two": self.get_number(12, 12),
            "adc_channel_three": self.get_number(24, 12),
            "adc_channel_four": self.get_number(36, 12),
            "adc_channel_five": self.get_number(48, 12)
        }
