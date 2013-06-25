__author__ = 'Will Hart'

from tornado.web import RequestHandler


class CategoriesHandler(RequestHandler):
    def get(self):
        """
        handles a GET request to /categories by writing a
        JSON list of categories
        """

        # TODO implement
        json = """{
    "data": [
        {
            "id": 1,
            "sessionId": 1,
            "variableName": "Acceleration",
            "selected": false
        }, {
            "id": 2,
            "sessionId": 1,
            "variableName": "Steering Input",
            "selected": false
        }, {
            "id": 3,
            "sessionId": 1,
            "variableName": "Brake",
            "selected": false
        }, {
            "id": 4,
            "sessionId": 1,
            "variableName": "Temperature",
            "selected": false
        }
    ]
}"""

        self.content_type = "application/json"
        self.write(json)


class CacheHandler(RequestHandler):
    def get(self, since=None):
        """
        handles a GET request to /cache by writing a
        JSON list of the last 50 values for each variable.

        If an argument is provided for "since" then only
        return values since that date. Otherwise return last 50
        """

        # TODO implement
        if since:
            json = """{
    "data": [
        {
            "id": 5,
            "sessionId": 1,
            "category": 3,
            "timeLogged": "13/01/2014 12:59:09.47",
            "value": 3.0
        },
        {
            "id": 6,
            "sessionId": 1,
            "category": 1,
            "timeLogged": "13/01/2014 12:59:12.78",
            "value": 4.0
        }
    ]
}"""
        else:
            json = """{
    "data": [
        {
            "id": 1,
            "sessionId": 1,
            "category": 3,
            "timeLogged": "13/01/2014 12:59:04.325",
            "value": 9.75
        },
        {
            "id": 2,
            "sessionId": 1,
            "category": 3,
            "timeLogged": "13/01/2014 12:59:06.575",
            "value": 10.05
        },
        {
            "id": 3,
            "sessionId": 1,
            "category": 1,
            "timeLogged": "13/01/2014 12:59:04.325",
            "value": 3.25
        },
        {
            "id": 4,
            "sessionId": 1,
            "category": 1,
            "timeLogged": "13/01/2014 12:59:06.575",
            "value": 11.27
        }
    ]
}"""

        self.content_type = "application/json"
        self.write(json)


class DownloadHandler(RequestHandler):
    def get(self, session_id):
        """
        handles a GET request to /download/{id} by requesting a download
        from the data logger for the given session ID and then returning a
        complete list of variable and values that were recorded during this
        logging session.
        """

        # TODO implement
        json = """{
    "session_id": 1,
    "timeStarted": "13/01/2014 12:59:06.575",
    "timeStopped": "13/01/2014 12:59:06.695",
    "data": [
        {
            "id": 1,
            "sessionId": 1,
            "category": 3,
            "timeLogged": "13/01/2014 12:59:04.325",
            "value": 9.75
        },
        {
            "id": 2,
            "sessionId": 1,
            "category": 3,
            "timeLogged": "13/01/2014 12:59:06.575",
            "value": 10.05
        },
        {
            "id": 3,
            "sessionId": 1,
            "category": 1,
            "timeLogged": "13/01/2014 12:59:04.325",
            "value": 3.25
        },
        {
            "id": 4,
            "sessionId": 1,
            "category": 1,
            "timeLogged": "13/01/2014 12:59:06.575",
            "value": 11.27
        }
    ]
}"""

        self.content_type = "application/json"
        self.write(json)


class SessionsHandler(RequestHandler):
    def get(self):
        """
        handles a GET request to /sessions and returns a complete
        list of logging sessions that are available for view or download
        """

        # TODO implement
        json = """{
    "data": [
        {
            "id": 1,
            "available": true,
            "timeStarted": "13/01/2014 12:59:00.054",
            "timeStopped": "13/01/2014 12:59:06.985",
            "readings": 127
        },
        {
            "id": 2,
            "available": false,
            "timeStarted": "13/01/2014 12:59:00.054",
            "timeStopped": "13/01/2014 12:59:06.985",
            "readings": 3
        },
        {
            "id": 3,
            "available": false,
            "timeStarted": "13/01/2014 12:59:00.054",
            "timeStopped": "13/01/2014 12:59:06.985",
            "readings": 77
        },
        {
            "id": 4,
            "available": false,
            "timeStarted": "13/01/2014 12:59:00.054",
            "timeStopped": "13/01/2014 12:59:06.985",
            "readings": 953
        }
    ]
}"""

        self.content_type = "application/json"
        self.write(json)


class SessionHandler(RequestHandler):
    def get(self, session_id):
        """
        handles a GET request to /session/{id} and returns
        a complete list of data relating to this session
        """

        # TODO implement
        json = """{
    "data": [
        {
            "id": 1,
            "sessionId": 1,
            "category": 3,
            "timeLogged": "13/01/2014 12:59:04.325",
            "value": 9.75
        },
        {
            "id": 2,
            "sessionId": 1,
            "category": 3,
            "timeLogged": "13/01/2014 12:59:06.575",
            "value": 10.05
        },
        {
            "id": 3,
            "sessionId": 1,
            "category": 1,
            "timeLogged": "13/01/2014 12:59:04.325",
            "value": 3.25
        },
        {
            "id": 4,
            "sessionId": 1,
            "category": 1,
            "timeLogged": "13/01/2014 12:59:06.575",
            "value": 11.27
        },
        {
            "id": 5,
            "sessionId": 1,
            "category": 3,
            "timeLogged": "13/01/2014 12:59:09.47",
            "value": 3.0
        },
        {
            "id": 6,
            "sessionId": 1,
            "category": 1,
            "timeLogged": "13/01/2014 12:59:12.78",
            "value": 4.0
        }
    ]
}"""

        self.content_type = "application/json"
        self.write(json)


class ConfigHandler(RequestHandler):
    def get(self):
        """
        handles a GET request to /config and returns
        a complete list of data relating to this session
        """

        # TODO implement
        json = """{
                "loggerPort": 8988,
                "loggerIp": "192.168.1.79",
                "clientPort": 8989,
                "clientIp": "192.168.1.80",
                "sampleRate": 60,
                "clientRefreshRate": 1,
                "sessionId": -1
            }"""

        self.content_type = "application/json"
        self.write(json)

    def post(self):
        """
        handles a POST request to /config and saves
        updated configuration information to the data logger
        """

        # TODO implement
        self.content_type = "application/json"
        self.write("{'response': 'ok'}")
