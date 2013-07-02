__author__ = 'Will Hart'

import logging

from blitz.data.database import DatabaseClient
from blitz.io.serial import SerialManager
import blitz.web.api as blitz_api
import blitz.web.http as blitz_http


#import json
import os.path

import tornado.httpserver
import tornado.ioloop
import tornado.web

from blitz.io.boards import BoardManager


class Config(object):
    """
    Holds configuration for a client application
    """

    settings = {}

    def __init__(self):
        """
        Sets up default settings
        """
        self.settings = {
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
            "static_path": os.path.join(os.path.dirname(__file__), "static"),
            "database_path": os.path.join(os.path.dirname(__file__), "data", "app.db"),
            "port": 8989,
            "autoescape": None,
            "debug": True
        }

    def get(self, key):
        """
        Gets an item from settings

        :raises: KeyError if the item doesn't exist
        :returns: A value corresponding to the given key
        """
        if key in self.settings.keys():
            return self.settings[key]
        raise KeyError("Unknown configuration setting - " + key)

    def set(self, key, value):
        """
        Sets the given configuration key to value

        :param key: the key to set
        :param value: the value to set the key to
        :returns: the value that was set
        """
        self.settings[key] = value
        return value

    def __getitem__(self, item):
        """
        A custom implementation of dict getters
        """
        return self.get(item)

    def __setitem__(self, key, value):
        """
        A custom implementation of dict setters
        """
        return self.set(key, value)


class Application(object):
    """
    A basic application which exposes the Api and HTTP request handlers
    provided by Tornado
    """

    io_loop = None

    def __init__(self):
        """
        Create a new client web application, setting defaults
        """

        # create a file logger and set it up for logging to file
        logging.basicConfig(filename='log.txt', level=logging.DEBUG,
                            format='[%(asctime)s %(levelname)-10s %(threadName)-10s]:    %(message)s')
        ch = logging.StreamHandler()
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(ch)

        # load configuration
        self.config = Config()

        # create a database connection
        self.data = DatabaseClient()

        # TODO - database should persist
        self.data.create_tables()
        self.data.load_fixtures()
        self.logger.debug("Initialised client database")

        # create a board manager
        self.board_manager = BoardManager(self.data)

        # create a serial manager
        self.serial_manager = SerialManager.Instance()

        # create an application
        self.application = tornado.web.Application([
                                                   (r'/', blitz_http.IndexHandler),
                                                   (r'/categories', blitz_api.CategoriesHandler),
                                                   (r'/cache', blitz_api.CacheHandler),
                                                   (r'/cache/(?P<since>[^\/]+)', blitz_api.CacheHandler),
                                                   (r'/download/(?P<session_id>[^\/]+)', blitz_api.DownloadHandler),
                                                   (r'/session/(?P<session_id>[^\/]+)', blitz_api.SessionHandler),
                                                   (r'/sessions', blitz_api.SessionsHandler),
                                                   (r'/config', blitz_api.ConfigHandler),
                                                   (r'/connect', blitz_http.ConnectHandler),
                                                   (r'/start', blitz_http.StartHandler),
                                                   (r'/stop', blitz_http.StopHandler),
                                                   (r'/status', blitz_http.StatusHandler)
                                                   ], **self.config.settings)
        self.logger.debug("Initialised client application")

        # create an HTTP server
        self.http_server = tornado.httpserver.HTTPServer(self.application)
        self.logger.info("Initialised client HTTP server")

        # save variables for later
        self.application.settings['socket'] = None
        self.application.settings['data'] = self.data
        self.application.settings['board_manager'] = self.board_manager
        self.application.settings['serial_manager'] = self.serial_manager

    def run(self):
        """
        Starts the application
        """

        # start listening on the configured port and IP
        self.http_server.listen(self.config['port'])
        self.logger.info("HTTP server started listening on port " + str(self.config['port']))

        # start the IO loop
        try:
            self.io_loop = tornado.ioloop.IOLoop.instance()
            self.io_loop.start()
            self.logger.debug("HTTP server started IO loop")

        finally:
            tcp = self.application.settings['socket']
            if tcp is not None:
                tcp.disconnect()

            self.io_loop.stop()
            self.logger.info("Stopped IO loop resources")
