__author__ = 'Will Hart'

import json
import time
from tornado.web import RequestHandler

from blitz.data.models import *


class ApiRequestHandler(RequestHandler):
    def generate_status_response(app):
        """generates a status response"""
        tcp = app.application.settings['socket']
        data = app.settings['data']

        if tcp is None:
            time.sleep(1.5)  # let tcp get populated?
            tcp = app.application.settings['socket']

        counter = 0
        while tcp is not None and tcp.is_busy():
            counter += 1
            time.sleep(0.2)
            if counter > 5:
                break

        response = {
            "logging": False if tcp is None else tcp.is_logging(),
            "connected": False if tcp is None else tcp.is_connected(),
            "errors": []
        }

        errors = data.all(Notification)
        for e in errors:
            response['errors'].append(e.to_dict())

        return response


class CategoriesHandler(ApiRequestHandler):
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
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(json_obj))


class CacheHandler(ApiRequestHandler):
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

        if since > 0:
            result = data.get_cache(since)
        else:
            result = data.get_cache()

        for r in result:
            data_objs.append(r.to_dict())

        json_objs['data'] = data_objs

        self.content_type = "application/json"
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(json_objs))


class DownloadHandler(ApiRequestHandler):
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
        json_objs['timeStarted'] = session.timeStarted
        json_objs['timeStopped'] = session.timeStopped
        json_objs['numberOfReadings'] = len(data_objs)
        json_objs['data'] = data_objs

        self.content_type = "application/json"
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(json_objs))


class SessionsHandler(ApiRequestHandler):
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
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(json_objs))


class SessionHandler(ApiRequestHandler):
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
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(json_objs))


class ConfigHandler(ApiRequestHandler):
    def get(self):
        """
        handles a GET request to /config and returns
        a complete list of data relating to this session
        """

        data = self.settings['data']
        json_objs = {}
        result = data.all(Config)

        for r in result:
            json_objs[r.key] = r.value

        self.content_type = "application/json"
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(json_objs))

    def post(self):
        """
        handles a POST request to /config and saves
        updated configuration information to the data logger
        """

        # get the response body as a dict
        data = self.settings['data']
        config_json = self.get_argument('config', "{}")
        config = json.loads(config_json)

        for k in config.keys():
            data.set_config(k, config[k])

        self.content_type = "application/json"
        self.set_header("Cache-control", "no-cache")
        self.write("{'response': 'ok'}")


class StatusHandler(ApiRequestHandler):

    def get(self):
        """Get the current system status"""
        self.content_type = "application/json"
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(self.generate_status_response()))


class ErrorHandler(ApiRequestHandler):

    def get(self, error_id):
        data = self.settings['data']
        data.handle_error(error_id)

        self.content_type = "application/json"
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(self.generate_status_response()))
