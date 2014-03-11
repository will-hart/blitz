__author__ = 'Will Hart'

from blitz.communications.tcp import TcpBase
from blitz.utilities import blitz_timestamp

time0 = blitz_timestamp()
time1 = time0 - 1
time2 = time0 - 2
time3 = time0 - 3
time4 = time0 - 4
time5 = time0 - 5
time6 = time0 - 6

READING_FIXTURES = [
    {"sessionId": 1, "timeLogged": time3, "categoryId": 1, "value": 3.75},
    {"sessionId": 1, "timeLogged": time2, "categoryId": 1, "value": 9.12},
    {"sessionId": 1, "timeLogged": time4, "categoryId": 1, "value": 7.56},
    {"sessionId": 1, "timeLogged": time1, "categoryId": 2, "value": 5.2},
    {"sessionId": 1, "timeLogged": time0, "categoryId": 2, "value": 4.3},
    {"sessionId": 1, "timeLogged": time5, "categoryId": 2, "value": 1.23}
]

CACHE_FIXTURES = [
    {"timeLogged": time3, "categoryId": 1, "value": 3.75},
    {"timeLogged": time2, "categoryId": 1, "value": 9.12},
    {"timeLogged": time4, "categoryId": 1, "value": 7.56},
    {"timeLogged": time1, "categoryId": 2, "value": 5.2},
    {"timeLogged": time0, "categoryId": 2, "value": 4.3},
    {"timeLogged": time5, "categoryId": 2, "value": 1.23}

]

CATEGORY_FIXTURES = [
    {"variableName": "adc_channel_one"},
    {"variableName": "adc_channel_two"},
    {"variableName": "adc_channel_three"}
]

SESSION_FIXTURES = [
    {"available": True, "ref_id": 1, "timeStarted": time4, "timeStopped": time2, "numberOfReadings": 2},
    {"available": False, "ref_id": 2, "timeStarted": time2, "timeStopped": time0, "numberOfReadings": 2}
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


class TcpClientMock(TcpBase):
    """
    A class for mocking TCP operations (client side) during unit testing
    """
    def __init__(self):
        self.last_sent = ""
        super(TcpClientMock, self).__init__(host="*", port="12345")

    def do_send(self, msg):
        """Mocks sending a TCP message by printing to stdout"""
        print "[SEND] ", msg
        self.last_sent = msg

    def receive_message(self, msg):
        """Log then process the message using the super class"""
        print "[RECEIVE] ", msg
        super(TcpClientMock, self).receive_message(msg)

    def __handle_receive(self, cmd):
        pass
