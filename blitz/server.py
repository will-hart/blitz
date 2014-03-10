__author__ = 'Will Hart'

import json
import logging
import os

from blitz.constants import CommunicationCodes
from blitz.communications.netscanner import NetScannerManager
from blitz.communications.rs232 import SerialManager
import blitz.communications.signals as sigs
from blitz.communications.tcp import TcpBase


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
        self.logger.info("Loading Server Configuration")
        self.settings = {
            "application_path": os.path.dirname(__file__),
            "tcp_port": 8999,
            "database_port": 6379,
            "debug": True,
            "use_netscanner": False
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


class ApplicationServer(object):
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
                            format='%(asctime)-27s %(levelname)-10s %(name)-25s %(threadName)-15s   %(message)s')
        ch = logging.StreamHandler()
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(ch)

        # load configuration
        self.config = Config()

        # TODO: Implement plugin interface
        # create a serial server
        self.serial_server = SerialManager.Instance()
        self.logger.info("Initialised serial manager")

        # TODO: Implement plugin interface
        # create a NetScanner server
        if (self.config['use_netscanner']):
            db = self.serial_server.database
            self.netscanner = [
                NetScannerManager(db, self.config['netscanner_one_ip'], "0A") # ,
                #NetScannerManager(db, self.config['netscanner_two_ip'], "0B")
            ]

        # hook up signals
        sigs.client_requested_session_list.connect(self.update_session_list)
        sigs.server_status_request.connect(self.serve_client_status)
        sigs.client_requested_download.connect(self.serve_client_download)
        sigs.board_list_requested.connect(self.send_connected_boards)

        # start the TCP server
        self.tcp = TcpBase(port=self.config["tcp_port"])
        self.tcp.create_server()
        self.is_running = True
        self.logger.info("Started TCP on port %s" % self.config["tcp_port"])

    def update_session_list(self, args):
        """
        Sends the client the list of logged sessions
        """
        self.logger.debug("Server sending out updated session list")

        if self.serial_server.database is None:
            self.logger.warn("Unable to generate session list - no database")
            self.tcp.send(CommunicationCodes.Negative)
        else:
            sessions = self.serial_server.database.build_client_session_list()
            sessions_string = "\n".join([x for x in sessions])
            sessions_string += "\n" + CommunicationCodes.Negative
            self.tcp.send(sessions_string)
            self.logger.debug("Session list queued for sending")

    def serve_client_status(self, args):
        """
        Sends the client the last serial message received from a board

        # TODO - improve to send the last serial message from each connected given board in serial_mapping
        """
        message = self.serial_server.database.get_latest_from_session(self.serial_server.database.session_id)
        self.tcp.send(message)

    def serve_client_download(self, session_id):
        # get all the session data from the database
        session_data = self.serial_server.database.get_all_from_session(session_id)

        # split into rows of 100 readings then pass to the state manager for dispatch
        # todo set the '100' value to a constant
        split_session_data = [session_data[i:i + 100] for i in range(0, len(session_data), 100)]
        self.tcp.send(split_session_data)

    def send_connected_boards(self):
        """
        Handles the BOARDS request from the client, wanting to know which boards are connected
        """
        boards = "BOARDS " + " ".join([x for x in self.serial_server.serial_mapping.keys()])

        if self.config['use_netscanner']:
            boards += " ".join([x.board_id for x in self.netscanner])

        self.tcp.send(boards)

    def __del__(self):
        self.logger.warning("Shutting down server Application")
