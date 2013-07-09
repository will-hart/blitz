__author__ = 'Will Hart'

import json
import logging
import os

from blitz.io.tcp import TcpClient
from blitz.web.api import ApiRequestHandler


class IndexHandler(ApiRequestHandler):

    def get(self):
        # just read the file in to prevent tornado from processing handlebars
        resp_file = open(os.path.join(self.application.settings['template_path'], "index.html"))
        self.write(resp_file.read())


class ConnectHandler(ApiRequestHandler):

    logger = logging.getLogger(__name__)

    def get(self):
        """Toggles the TCP connection"""
        tcp = self.application.settings['socket']

        if tcp is None:
            # we are connecting
            self.logger.debug("Created TCP connection at client request")
            tcp = TcpClient("127.0.0.1", 8999)  # TODO get from config
            tcp.start()
            tcp.connect()
            self.application.settings['socket'] = tcp
        else:
            tcp.disconnect()
            self.logger.debug("Closed TCP connection at client request")
            self.application.settings['socket'] = None

            # write a connection error to database for the user
            data = self.application.settings['data']
            data.log_error("Unable to connect to the network")

        self.content_type = "application/json"
        self.write(json.dumps(self.generate_status_response()))


class StartHandler(ApiRequestHandler):

    logger = logging.getLogger(__name__)

    def get(self):
        """Attempts to start logging"""
        tcp = self.application.settings['socket']
        data = self.application.settings['data']

        if tcp is None:
            self.logger.warning("Attempt to start logging on TCP connection failed - there is no TCP connection")
        else:
            self.logger.debug("Web client requested logging start")
            tcp.request_start()

        # clear the cache before starting
        data.clear_cache()

        self.content_type = "application/json"
        self.write(json.dumps(self.generate_status_response()))


class StopHandler(ApiRequestHandler):

    logger = logging.getLogger(__name__)

    def get(self):
        """Attempts to start logging"""
        tcp = self.application.settings['socket']

        if tcp is None:
            self.logger.warning("Attempt to stop logging on TCP connection failed - there is no TCP connection")

        else:
            self.logger.debug("Web client requested logging stop")
            tcp.request_stop()

        self.content_type = "application/json"
        self.write(json.dumps(self.generate_status_response()))
