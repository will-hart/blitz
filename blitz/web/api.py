__author__ = 'Will Hart'

from blitz.data.models import *
from blitz.utilities import to_blitz_date
import json
from tornado.web import RequestHandler


class CategoriesHandler(RequestHandler):
    def get(self):
        """
        handles a GET request to /categories by writing a
        JSON list of categories currently in the cache
        """

        data = self.settings['data']
        result = data.get_cache_variables()
        json_obj = {}
        data_objs = []

        for r in result:
            data_objs.append(r.to_dict())

        # remove the last comma
        json_obj['data'] = data_objs

        # write the response
        self.content_type = "application/json"
        self.write(json.dumps(json_obj))


class CacheHandler(RequestHandler):
    def get(self, since=None):
        """
        handles a GET request to /cache by writing a
        JSON list of the last 50 values for each variable.

        If an argument is provided for "since" then only
        return values since that date. Otherwise return last 50
        """

        data = self.settings['data']
        json_objs = {}
        data_objs = []

        if since is not None:
            result = data.get_cache(float(since))
        else:
            result = data.get_cache()

        for r in result:
            data_objs.append(r.to_dict())

        json_objs['data'] = data_objs

        self.content_type = "application/json"
        self.write(json.dumps(json_objs))


class DownloadHandler(RequestHandler):
    def get(self, session_id):
        """
        handles a GET request to /download/{id} by requesting a download
        from the data logger for the given session ID and then returning a
        complete list of variable and values that were recorded during this
        logging session.
        """

        data = self.settings['data']
        json_objs = {}
        data_objs = []
        readings = data.get_session_readings(session_id)
        session = data.get_by_id(Session, session_id)

        for r in readings:
            data_objs.append(r.to_dict())

        json_objs['sessionId'] = session_id
        json_objs['timeStarted'] = to_blitz_date(session.timeStarted)
        json_objs['timeStopped'] = to_blitz_date(session.timeStopped)
        json_objs['numberOfReadings'] = len(data_objs)
        json_objs['data'] = data_objs

        self.content_type = "application/json"
        self.write(json.dumps(json_objs))


class SessionsHandler(RequestHandler):
    def get(self):
        """
        handles a GET request to /sessions and returns a complete
        list of logging sessions that are available for view or download
        """
        data = self.settings['data']
        json_objs = {}
        data_objs = []
        result = data.all(Session)

        for r in result:
            data_objs.append(r.to_dict())

        json_objs['data'] = data_objs

        self.content_type = "application/json"
        self.write(json.dumps(json_objs))


class SessionHandler(RequestHandler):
    def get(self, session_id):
        """
        handles a GET request to /session/{id} and returns
        a complete list of data relating to this session
        """

        data = self.settings['data']
        json_objs = {}
        data_objs = []
        result = data.get_session_readings(session_id)

        for r in result:
            data_objs.append(r.to_dict())

        json_objs['data'] = data_objs
        self.content_type = "application/json"
        self.write(json.dumps(json_objs))


class ConfigHandler(RequestHandler):
    def get(self):
        """
        handles a GET request to /config and returns
        a complete list of data relating to this session
        """

        data = self.settings['data']
        json_objs = {}
        data_objs = []
        result = data.all(Config)

        for r in result:
            data_objs.append(r.to_dict())

        json_objs['data'] = data_objs

        self.content_type = "application/json"
        self.write(json.dumps(json_objs))

    def post(self):
        """
        handles a POST request to /config and saves
        updated configuration information to the data logger
        """

        # get the response body as a dict
        config_json = self.get_argument('config', "{}")
        config = json.loads(config_json)


        # TODO implement
        self.content_type = "application/json"
        self.write("{'response': 'ok'}")
