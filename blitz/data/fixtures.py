__author__ = 'Will Hart'

import datetime

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
