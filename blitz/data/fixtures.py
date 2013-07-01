from random import random

__author__ = 'Will Hart'

import datetime

from blitz.io.boards import BaseExpansionBoard
from blitz.io.tcp import TcpClient

time0 = datetime.datetime.now()
time1 = datetime.datetime.now() - datetime.timedelta(seconds=1)
time2 = datetime.datetime.now() - datetime.timedelta(seconds=2)
time3 = datetime.datetime.now() - datetime.timedelta(seconds=3)
time4 = datetime.datetime.now() - datetime.timedelta(seconds=4)

READING_FIXTURES = [
    {"sessionId": 1, "timeLogged": time3, "categoryId": 1, "value": 3.75},
    {"sessionId": 1, "timeLogged": time2, "categoryId": 1, "value": 9.12},
    {"sessionId": 1, "timeLogged": time1, "categoryId": 2, "value": 5.2},
    {"sessionId": 1, "timeLogged": time0, "categoryId": 2, "value": 4.3}
]

CACHE_FIXTURES = [
    {"timeLogged": time3, "categoryId": 1, "value": 3.75},
    {"timeLogged": time2, "categoryId": 1, "value": 9.12},
    {"timeLogged": time1, "categoryId": 2, "value": 5.2},
    {"timeLogged": time0, "categoryId": 2, "value": 4.3}
]

CATEGORY_FIXTURES = [
    {"variableName": "Accelerator"},
    {"variableName": "Brake"},
    {"variableName": "Third"}
]

SESSION_FIXTURES = [
    {"available": True, "timeStarted": time4, "timeStopped": time2, "numberOfReadings": 2},
    {"available": False, "timeStarted": time2, "timeStopped": time0, "numberOfReadings": 2}
]

CONFIG_FIXTURES = [
    {"key": "loggerPort", "value": "8989"},
    {"key": "loggerIp", "value": "192.168.1.79"},
    {"key": "clientPort", "value": "8988"},
    {"key": "clientIp", "value": "192.168.1.79"},
    {"key": "sampleRate", "value": "50"},
    {"key": "clientRefreshRate", "value": "2"}
]


def generate_objects(model, fixtures):
    """
    Generate a list of objects of the provided model type with the data
    given in the fixtures list of dictionaries
    """
    res = []
    for f in fixtures:
        res.append(model(**f))
    return res


class TcpClientMock(TcpClient):
    """
    A class for mocking TCP operations (client side) during unit testing
    """

    def send(self, msg):
        """Mocks sending a TCP message by printing to stdout"""
        print "[SEND] ", msg

    def parse_reading(self, msg):
        """Mocks processing a data message by printing message to stdout, then pass to super class"""
        print "[PARSE] ", msg
        super(TcpClientMock, self).parse_reading(msg)

    def process_message(self, msg):
        """Log then process the message using the super class"""
        print "[RECEIVE] ", msg
        super(TcpClientMock, self).process_message(msg)


class ExpansionBoardMock(BaseExpansionBoard):
    """
    Test the parsing abilities of expansion boards
    """

    def identify_board(self):
        self['id'] = 0
        self['description'] = "Expansion Board Mock For Testing"

    def get_variables(self):
        return {
            "flag_one": self.get_flag(0),
            "flag_two": self.get_flag(1),
            "flag_three": self.get_flag(2),
            "flag_four": self.get_flag(3),
            "flag_five": self.get_flag(4),

            "type": self['type'],

            "full_payload": self.get_raw_payload(),

            "variable_a": self.get_number(0, 16),
            "variable_b": self.get_number(16, 16)
        }


class TcpServerFixtureGenerator(object):
    """Generates random dictionary of fixtures for the TCP server to send as updates"""

    @classmethod
    def generate_cache(cls, categories):
        """Generate one random reading (between 0 and 10) for each given category"""

        readings = []

        # generate readings
        for cat in categories:
            readings.append(
                {"sessionId": 1, "timeLogged": datetime.datetime.now(), "categoryId": cat, "value": random() * 10})

        # add the readings to the database
        return readings
