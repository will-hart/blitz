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
from blitz.communications.tcp import TcpCommunicationException, TcpBase
from blitz.server import Config


class ApplicationClient(object):
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

        # create an empty TCP connection
        self.tcp = None

        # create a board manager
        self.board_manager = BoardManager(self.data)

        # save variables for later
        self.config['board_manager'] = self.board_manager

        # set up a cache
        self.cache = self.data.get_cache()
        self.variable_cache = self.data.get_cache_variables()

        # subscribe to signals
        sigs.cache_line_received.connect(self.cache_line_received)
        sigs.client_requested_download.connect(self.send_download_request)
        sigs.client_requested_session_list.connect(self.request_session_list)
        sigs.board_command_received.connect(self.send_command)
        sigs.force_board_reset.connect(self.force_board_reset)
        sigs.board_list_requested.connect(self.send_boards_command)
        sigs.board_list_received.connect(self.process_boards_command)
        sigs.delete_server_session.connect(self.request_session_delete)

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
        results = self.board_manager.parse_message(message)
        self.update_interface(results)

    def send_download_request(self, session_id):
        """
        Sends a request for downloading a given session ID to the data logger
        """
        self.logger.debug("Handling client download request")

        if self.tcp is None:
            sigs.process_finished.send()
            self.logger.debug("Failed to handle client download request - no TCP connection")
            self.data.log_error(
                "Unable to request download for session #%s as the logger is not connected" % session_id)
            return

        # delete old session data
        self.data.clear_session_data(session_id)
        self.tcp.send(CommunicationCodes.composite(CommunicationCodes.Download, session_id))

    def connect_to_logger(self, args=None):
        """
        Handles a connection request from the client and establishes a TCP connection
        with the data logger.  If a connection already exists, close it and reopen
        """


        if self.tcp is None:
            # we are connecting
            sigs.process_started.send("Creating connection to data logger")

            self.logger.debug("Creating TCP connection {0}:{1}".format(
                self.config["server_ip"], self.config["server_port"]))
            try:
                self.tcp = TcpBase(self.config["server_ip"], self.config["server_port"])
                self.tcp.create_client()
            except TcpCommunicationException:
                self.data.log_error("Communication error with the board - connection closed")
                self.tcp.stop()
                self.tcp = None

        else:
            sigs.process_started.send("Closing connection to data logger")
            self.tcp.stop()
            self.logger.debug("Closed TCP connection at client request")
            self.tcp = None
            sigs.process_finished.send()

    def start_logging(self, args=None):
        """
        Sends a 'start logging' signal to the data logger
        """
        sigs.process_started.send("Getting logger to start logging")

        if self.tcp is None:
            self.logger.warning("Attempt to start logging on TCP connection failed - there is no TCP connection")
        else:
            self.logger.debug("Web client requested logging start")
            self.tcp.send(CommunicationCodes.Start)

    def stop_logging(self, args=None):
        """
        Sends a 'stop logging' signal to the data logger
        """
        sigs.process_started.send("Getting logger to stop logging")

        if self.tcp is None:
            self.logger.warning("Attempt to stop logging on TCP connection failed - there is no TCP connection")

        else:
            self.logger.debug("Web client requested logging stop")
            self.tcp.send(CommunicationCodes.Stop)

    def request_session_list(self, args=None):
        """
        Gets an update of the session list from the device. Must usually be called when in IDLE state so the
        UI should prevent calling at other times
        """
        self.tcp.send(CommunicationCodes.GetSessions)

    def request_session_delete(self, session_id):
        """
        Send a request for the server to delete a session ID from memory
        """
        self.tcp.send(CommunicationCodes.composite(CommunicationCodes.Delete, session_id))

    def update_interface(self, data, replace_existing=False):
        """
        Updates the user interface with new cache data received.  This method generates the required data structure,
        the actual interface implementation is provided by the inheriting class.  Note that this means the inheriting
        class should call `results = super(...).update_interface` to gather the data in the correct format.

        :param data: A list of Cache models or Reading models to convert into a dictionary: {'variable_name': [[x][y]] }
        :param replace_existing: If True, appends to existing cache, if False, replaces cache? Defaults to False

        :returns: The dictionary of readings required to update the UI, or None if no data is found
        """

        result = {}

        for item in data:
            cat_id = (str(item['categoryId']), item['categoryName'])
            if not cat_id in result.keys():
                result[cat_id] = [[], []]  # set up an empty list

            result[cat_id][0].append(item['timeLogged'])
            result[cat_id][1].append(item['value'])

        return None if len(result.keys()) == 0 else result

    def send_command(self, command):
        """
        Sends a message to the board with the given id.  The message should be packed as a hex string

        :param command: the hex payload to send
        """
        self.tcp.send(CommunicationCodes.composite(
            CommunicationCodes.Board, "{0} {1}".format(command[:2], command[2:])))

    def force_board_reset(self, args=None):
        """
        Forces the logger to be reset, can fix some errors
        """
        self.tcp.send(CommunicationCodes.Reset)

    def send_boards_command(self, args=None):
        """
        Requests a list of connected expansion boards to the data logger
        """
        self.tcp.send(CommunicationCodes.Boards)

    def process_boards_command(self, args):
        """
        Process a BOARDS response received from the server

        :param args: A string containing "BOARDS " followed by a list of board IDs
        """

        if args[0:6] != CommunicationCodes.Boards:
            self.logger.warning("Boards response does not match expected format - {0}".format(args))
            return

        board_descriptions = self.board_manager.get_board_descriptions(args[7:].split())
        sigs.board_list_processed.send(board_descriptions)

    def __del__(self):
        """
        A destructor, run when the application is closing
        """
        self.logger.warning("Closing Client Application")

