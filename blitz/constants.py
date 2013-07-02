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

BOARD_MESSAGE_MAPPING = {
    "sender": {"start": 0, "end": 8},
    "type": {"start": 8, "end": 11},
    "flag1": {"start": 11},
    "flag2": {"start": 12},
    "flag3": {"start": 13},
    "flag4": {"start": 14},
    "flag5": {"start": 15},
    "timestamp": {"start": 16, "end": 32},
    "payload": {"start": 32, "end": 64}
}
