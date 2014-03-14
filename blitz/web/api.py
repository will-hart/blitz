__author__ = 'Will Hart'

import time
from tornado.web import RequestHandler

from blitz.data.models import *
import blitz.communications.signals as sigs


class ApiRequestHandler(RequestHandler):
    """
    A base API request handler class
    """

    def generate_status_response(self):
        """generates a status response"""
        tcp = self.application.settings['socket']
        data = self.settings['data']

        if tcp is None:
            time.sleep(1.0)  # let tcp get populated?
            tcp = self.application.settings['socket']

        # if the tcp is doing something, wait for it to finish before checking status
        # but don't wait too long or the browser will get bored :)
        wait_counter = 0
        while tcp is not None and tcp.waiting and wait_counter < 20:
            time.sleep(0.1)

        response = {
            "logging": False if tcp is None else tcp.is_logging(),
            "connected": False if tcp is None else tcp.is_alive(),
            "errors": []
        }

        errors = data.all(Notification)
        for e in errors:
            response['errors'].append(e.to_dict())

        return response


class CategoriesHandler(ApiRequestHandler):
    """
    handles a GET request to /categories by writing a
    JSON list of categories currently in the cache
    """
    def get(self):

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
    """
    handles a GET request to /cache by writing a
    JSON list of the last 50 values for each variable.

    If an argument is provided for "since" then only
    return values since that date. Otherwise return last 50
    """
    def get(self, since=None):

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
    """
    handles a GET request to /download/{id} by requesting a download
    from the data logger for the given session ID and then returning a
    complete list of variable and values that were recorded during this
    logging session.
    """
    def get(self, session_id):

        sigs.client_requested_download.send(session_id)

        self.content_type = "application/json"
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps({"response": "processing"}))


class SessionsHandler(ApiRequestHandler):
    """
    handles a GET request to /sessions and returns a complete
    list of logging sessions that are available for view or download
    """
    def get(self):
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
    """
    handles a GET request to /session/{id} and returns
    a complete list of data relating to this session
    """
    def get(self, session_id):

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
    """
    An API handler which allows setting and retrieving of config settings
    """

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
    """Get the current system status"""
    def get(self):
        self.content_type = "application/json"
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(self.generate_status_response()))


class ErrorHandler(ApiRequestHandler):
    """Handles error messages"""
    def get(self, error_id):
        data = self.settings['data']
        data.handle_error(error_id)

        self.content_type = "application/json"
        self.set_header("Cache-control", "no-cache")
        self.write(json.dumps(self.generate_status_response()))
