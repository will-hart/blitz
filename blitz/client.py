__author__ = 'Will Hart'

import logging
import os.path
import tornado.httpserver
import tornado.ioloop
import tornado.web

from blitz.constants import CommunicationCodes
from blitz.data.database import DatabaseClient
from blitz.communications.boards import BoardManager
import blitz.communications.signals as sigs
import blitz.web.api as blitz_api
import blitz.web.http as blitz_http


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


class BaseApplicationClient(object):
    """
    A basic application which provides access method agnostic functionality
    for running a Blitz client side application.  Can be inherited to run
    web or desktop type applications
    """

    def __init__(self):
        """
        Create a new client web application, setting defaults
        """

        # create a file logger and set it up for logging to file
        logging.basicConfig(filename='client_log.txt', level=logging.DEBUG,
                            format='%(asctime)-27s %(levelname)-10s %(name)-25s %(threadName)-15s   %(message)s')
        ch = logging.StreamHandler()
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(ch)

        # load configuration
        self.config = Config()

        # create a database connection
        self.data = DatabaseClient(path=self.config['database_path'])
        self.data.clear_errors()
        self.logger.info("Initialised DatabaseClient")

        # create a board manager
        self.board_manager = BoardManager(self.data)

        # save variables for later
        self.config['socket'] = None
        self.config['data'] = self.data
        self.config['board_manager'] = self.board_manager

        # subscribe to signals
        sigs.cache_line_received.connect(self.cache_line_received)
        sigs.client_requested_download.connect(self.send_download_request)

    def run(self):
        """
        Starts the application.  Should be provided by implementation
        """
        pass

    def cache_line_received(self, message):
        """
        Handles receiving a line of information from the logger,
        and writing and parsing this to the temporary cache
        """
        self.board_manager.parse_message(message)

    def send_download_request(self, session_id):
        """
        Sends a request for downloading a given session ID to the data logger
        """
        self.logger.debug("Handling client download request")
        tcp = self.config['socket']

        if tcp is None:
            self.logger.debug("Failed to handle client download request - no TCP connection")
            self.data.log_error(
                "Unable to request download for session #%s as the logger is not connected" % session_id)
            return

        # delete old session data
        data = self.config['data']
        data.clear_session_data(session_id)
        tcp.send(CommunicationCodes.composite(CommunicationCodes.Download, session_id))

    def __del__(self):
        """
        A destructor, run when the application is closing
        """
        self.logger.warning("Closing Client Application")


class WebApplicationClient(BaseApplicationClient):
    """
    A basic application which exposes the Api and HTTP request handlers
    provided by Tornado
    """

    io_loop = None

    def __init__(self):
        """
        Create a new client web application, setting defaults
        """

        super(WebApplicationClient, self).__init__()

        # todo remove fixture loading
        try:
            self.data.load_fixtures()
            self.logger.info("Loaded fixtures")
        except Exception:
            pass

        # create an application
        self.application = tornado.web.Application([
                                                   (r'/', blitz_http.IndexHandler),
                                                   (r'/categories', blitz_api.CategoriesHandler),
                                                   (r'/cache', blitz_api.CacheHandler),
                                                   (r'/cache/(?P<since>[^\/]+)', blitz_api.CacheHandler),
                                                   (r'/download/(?P<session_id>[^\/]+)', blitz_api.DownloadHandler),
                                                   (r'/error/(?P<error_id>[^\/]+)', blitz_api.ErrorHandler),
                                                   (r'/session/(?P<session_id>[^\/]+)', blitz_api.SessionHandler),
                                                   (r'/sessions', blitz_api.SessionsHandler),
                                                   (r'/config', blitz_api.ConfigHandler),
                                                   (r'/status', blitz_api.StatusHandler),
                                                   (r'/connect', blitz_http.ConnectHandler),
                                                   (r'/start', blitz_http.StartHandler),
                                                   (r'/stop', blitz_http.StopHandler)
                                                   ], **self.config.settings)

        # create an HTTP server
        self.http_server = tornado.httpserver.HTTPServer(self.application)
        self.logger.debug("HTTPServer __init__")

        # save variables for later
        self.application.settings['socket'] = None
        self.application.settings['data'] = self.data
        self.application.settings['board_manager'] = self.board_manager

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
            self.logger.debug("Client HTTP IoLoop exited")

        finally:
            tcp = self.application.settings['socket']
            if tcp is not None:
                tcp.stop()
                self.logger.warning("Stopped TCP Socket")

            self.io_loop.add_callback(self.io_loop.stop)
            self.logger.warning("Stopped IO loop with callback")



