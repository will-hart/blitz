__author__ = 'Will Hart'

import datetime
from math import ceil
import time
from random import random

from bitstring import BitArray


def to_blitz_date(given_date):
    """
    Generates a blitz date string from a python datetime
    """
    return given_date.strftime("%d-%m-%Y %H:%M:%S") + "." + str(
        int(float(given_date.microsecond) / 1000.0))


def blitz_timestamp():
    """
    Generates the current timestamp in milliseconds since Unix epoch.
    This is a bit of a cludge to allow storing "decimal" number in sqlite.
    to convert to javascript datetime, this must be divided by 1000.0
    """
    return ceil(time.time() * 1000)


def generate_tcp_server_fixtures():
        """Generate a random reading at the given datetime for a BlitzBasic board"""

        # build the message preamble (first 48 bits)
        sender = BitArray(bin="0b00000001")
        msg_type = BitArray(bin="0b00000000")
        timestamp = BitArray(int=int(time.mktime(datetime.datetime.now().timetuple())), length=32)
        preamble = sender + msg_type + timestamp

        # generate reading
        # create the blitz basic variables
        part_one = BitArray(uint=int(random()*1024), length=12)
        part_two = BitArray(uint=int(random()*1024), length=12)
        part_three = BitArray(uint=int(random()*1024), length=12)
        part_four = BitArray(uint=int(random()*1024), length=12)
        part_five = BitArray(uint=int(random()*1024), length=12)
        payload = part_one + part_two + part_three + part_four + part_five + BitArray(bin="0b0000")

        # build the final message
        message = preamble + payload

        # add the readings to the database
        return message
