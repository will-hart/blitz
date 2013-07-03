__author__ = 'Will Hart'

import json
import logging
import os

from blitz.data.database import DatabaseServer
from blitz.io.serial import SerialManager

class Config(object):
    """
    Holds configuration for a client application
    """
    settings = {}

    logger = logging.getLogger(__name__)

    def __init__(self):
        """
        Sets up default settings
        """
        self.logger.debug("Loading Server Configuration")
        self.settings = {
            "application_path": os.path.dirname(__file__),
            "tcp_port": 8999,
            "database_port": 6379,
            "debug": True
        }

        self.load_from_file()

    def write_to_file(self):
        # take a defensive copy and remove the settings path, then convert to json
        config = self.settings.copy()
        del config["application_path"]
        json_str = json.dumps(config)

        # write to file
        with open(os.path.join(self.settings['application_path'], "config.json"), 'w') as f:
            f.write(json_str)

        self.logger.debug("Writing server configuration to file")

    def load_from_file(self):
        # read in the config file
        lines = ""

        try:
            with open(os.path.join(self.settings['application_path'], "config.json"), 'r') as f:
                lines = f.readlines()
        except IOError:
            self.write_to_file()
            return

        # convert to json
        json_lines = json.loads("\n".join([x for x in lines]))

        # save the config, avoiding "application_path"
        for key, val in json_lines.iteritems():
            if not key == "application_path":
                self.settings[key] = val

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
        self.write_to_file()
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

    def __init__(self):
        """
        Create a new client web application, setting defaults
        """

        # create a file logger and set it up for logging to file
        logging.basicConfig(filename='server_log.txt', level=logging.DEBUG,
                            format='[%(asctime)s %(levelname)-10s %(threadName)-10s]:    %(message)s')
        ch = logging.StreamHandler()
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(ch)

        # load configuration
        self.config = Config()

        # create a database connection
        self.data = DatabaseServer()
        self.data.start_session()
        self.logger.debug("Initialised server database")

        # create a serial server
        self.serial_server = SerialManager()
        self.logger.debug("Initialised serial manager")