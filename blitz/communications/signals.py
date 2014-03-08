__author__ = 'Will Hart'

from blinker import signal

#: Fired when the client has requested a connection to the data logger
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - BaseApplicationClient.__init__ >> BaseApplicationClient.connect_to_logger()
#:
#: Sent by:
#:  - ConnectHandler.get()
logger_connecting = signal('logger_connected')

#: Fired when the client receives a line of cached data
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - :mod:`ApplicationClient`.__init__ >> ApplicationClient.cache_line_received
#:
#: Sent by:
#:  - :mod:`ClientLoggingState`.receive_message
cache_line_received = signal('cache_line_received')

#: Fired when the expansion board receives a data row for processing
#: during a download.  Allows pre-processing of data
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - :mod:`BoardManager`.__init__ >> BoardManager.parse_session_message
#:
#: Sent by:
#:  - :mod:`BaseExpansionBoard`.parse_message
#:  - :mod:`ClientDownloadingState`.receive_message
data_line_received = signal('data_line_received')

#: Fired when a board has finished processing a data line
#:
#: Sent by:
#:  - :mod:`BaseExpansionBoard`.parse_message
data_line_processed = signal('data_line_processed')

#: Fired when expansion boards should be registered with the board manager
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - [Expansion Boards].register_signals >> BaseExpansionBoard.register_board
#:
#: Sent by:
#:  - :mod:`BaseExpansionBoard`.__init__
registering_boards = signal('registering_boards')

#: Fired when plugins are loaded
#:
#: Sent by:
#:  - :mod:`PluginMount`.register_plugin
plugin_loaded = signal('plugin_loaded')

#: Fired when logging starts on the server
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - :mod:`SerialManager`.__init__ >> SerialManager.start
#:
#: Sent by:
#:  - :mod:`ServerLoggingState`.enter_state
logging_started = signal('logging_started')

#: Fired when logging stops on the server
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - :mod:`SerialManager`.__init__ >> SerialManager.stop
#:
#: Sent by:
#:  - :mod:`ServerLoggingState`.receive_message
logging_stopped = signal('logging_stopped')

#: Fired when the client requests a status update from the server
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - ApplicationServer.__init__ >> ApplicationServer.serve_client_status
#:
#: Sent by:
#:  - :mod:`ServerLoggingState`.receive_message
server_status_request = signal('server_status_request')

#: Fired when the client has requested a status list update, TcpServer as argument
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - :mod:`ApplicationServer`.__init__ >> ApplicationServer.update_session_list
#:  - :mod:`ApplicationClient`.__init__ >> ApplicationClient.request_session_list
#:
#: Sent by:
#:  - :mod:`ServerIdleState`.receive_message
#:  - :mod:`MainBlitzWindow`.get_session_list
client_requested_session_list = signal('client_requested_session_list')

#: Fired when the client has a completed session list received from the server
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - :mod:`DatabaseClient`.__init__ >> DatabaseClient.update_session_list
#:
#: Sent by:
#:  - :mod:`ClientSessionListState`.go_to_state
client_session_list_updated = signal('client_session_list_updated')

#: Fired to let subscribers know a message is ready to be received
#: from the reply queue.  Normally should only be subscribed to by the Application
#:
#: Sent by:
#:  - :mod:`TcpBase`.run_server
#:  - :mod:`TcpBase`.run_client
tcp_message_received = signal('tcp_message_received')

#: Fired when a client requests a download of a particular session
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - :mod:`ApplicationServer`.__init__ >> ApplicationServer.serve_client_download
#:  - :mod:`ApplicationClient`.__init__ >> ApplicationClient.send_download_request
#:
#: Sent by:
#:  - :mod:`ServerDownloadingState`.enter_state
#:  - :mod:`DownloadHandler`.get
#:  - :mod:`blitz.ui.BlitzSessionWindow`.on_item_checked
client_requested_download = signal('client_requested_download')

#: Fired when a command was received from the desktop software for an expansion board
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - :mod:`SerialManager`.__init__ >> BoardManager.handle_board_command
#:  - :mod:`ApplicationClient`.__init__ >> ApplicationClient.send_command
#:
#: Sent by:
#:  - :mod:`ServerBaseState`.process_standard_messages
#:  - :mod:`CalibrationDialog`.step
board_command_received = signal('board_command_received')

#: Fired when the client loses the TCP connection (after three attempts)
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - `GUISignalEmitter`.__init__
#:
#: Sent by:
#:  - :mod:`TcpBase`.run_client
lost_tcp_connection = signal('lost_tcp_connection')

#: Fired when an asynchronous process starts to allow clients to update the UI
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - `GUISignalEmitter`.__init__
#:
#: Sent by:
#:  - :mod:`TcpBase`.run_client
process_started = signal('process_started')

#: Fired when an asynchronous process finishes to allow clients to update the UI
#:
#: Subscribers (subscribed in >> subscribed to):
#:  - `GUISignalEmitter`.__init__
#:
#: Sent by:
#:  - :mod:`TcpBase`.run_client
process_finished = signal('process_finished')
