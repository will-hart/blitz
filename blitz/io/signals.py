__author__ = 'Will Hart'

from blinker import signal

# fired when a new web client device connects
web_client_connected = signal('client_connected')

# fired when a web client disconnects
web_client_disconnected = signal('client_disconnected')

# fired when a new TCP client device connects
tcp_client_connected = signal('tcp_client_connected')

# fired when a TCP client disconnects
tcp_client_disconnected = signal('tcp_client_disconnected')

# fired when a server TCP connection is established
logger_connected = signal('logger_connected')

# fired when a server TCP connection is closed
logger_disconnected = signal('logger_disconnected')

# fired when the expansion board receives a data row for processing
# allows pre-processing of data
data_line_received = signal('data_line_received')

# fired when a variable is ready for entry into the database
# allows post processing of data
data_variable_decoded = signal('data_variable_decoded')

# fired when a board has finished processing a data line
data_line_processed = signal('data_line_processed')

# called when an expansion board is registered
expansion_board_registered = signal('expansion_board_registered')

# called when expansion boards should be registered with the board manager
registering_boards = signal('registering_boards')

# called when plugins are loaded
plugin_loaded = signal('plugin_loaded')
