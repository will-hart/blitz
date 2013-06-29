__author__ = 'Will Hart'

COMMAND_MESSAGE_BYTES = 8
SHORT_COMMAND_MESSAGE_BYTES = 2

# commands that are valid to send TO the server
# note only the command up to the space (if there is one) is included
VALID_SERVER_COMMANDS = [
    "START",
    "STOP",
    "STATUS",
    "DOWNLOAD",
    "BOARD",
    "LOGGING"
]

# commands that are valid to send TO the client
# note only the command up to the space (if there is one) is included
VALID_CLIENT_COMMANDS = [
    "ACK",
    "NACK",
    "INSESSION",
    "NOSESSION",
    "BOARDERROR",
    "NOBOARD",
    "ERROR",
    "READY"
]

MAX_MESSAGE_LENGTH = 64
