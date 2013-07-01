__author__ = 'Will Hart'

import json
import os
from tornado.web import RequestHandler

from blitz.io.tcp import TcpClient


class IndexHandler(RequestHandler):

    def get(self):
        # just read the file in to prevent tornado from processing handlebars
        resp_file = open(os.path.join(self.application.settings['template_path'], "index.html"))
        self.write(resp_file.read())


class ConnectHandler(RequestHandler):

    def get(self):
        """Toggles the TCP connection"""
        tcp = self.application.settings['socket']

        if tcp is None:
            # we are connecting
            tcp = TcpClient("127.0.0.1", 8999)  # TODO get from config
            self.application.settings['socket'] = tcp
            response = {'connected': True}
        else:
            tcp.disconnect()
            self.application.settings['socket'] = None
            response = {'connected': False}

        self.content_type = "application/json"
        self.write(json.dumps(response))


class StartHandler(RequestHandler):
    def get(self):
        """Attempts to start logging"""
        tcp = self.application.settings['socket']

        if tcp is None:
            response = {'logging': False, 'connected': False}

        else:
            tcp.request_start()
            response = {'logging': True, 'connected': True}

        self.content_type = "application/json"
        self.write(json.dumps(response))


class StopHandler(RequestHandler):
    def get(self):
        """Attempts to start logging"""
        tcp = self.application.settings['socket']

        if tcp is None:
            response = {'logging': False, 'connected': False}

        else:
            tcp.request_stop()
            response = {'logging': False, 'connected': True}

        self.content_type = "application/json"
        self.write(json.dumps(response))


class StatusHandler(RequestHandler):
    def get(self):
        """Get the current system status"""
        tcp = self.application.settings['socket']
        response = {
            "logging": False if tcp is None else tcp.is_logging(),
            "connected": tcp is None
        }

        self.content_type = "application/json"
        self.write(json.dumps(response))

