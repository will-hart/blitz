__author__ = 'Will Hart'

COMMAND_MESSAGE_BYTES = 8
SHORT_COMMAND_MESSAGE_BYTES = 2


class CommunicationCodes(object):
    """
    Provides "static" communication codes for Tcp Communication.  Usage is::

        from blitz.constants import CommunicationCodes
        tcp.send(CommunicationCodes.Acknowledge)
    """

    Acknowledge = "ACK"
    Negative = "NACK"
    Start = "START"
    Stop = "STOP"
    Update = "UPDATE"
    InSession = "INSESSION"
    NoSession = "NOSESSION"
    Download = "DOWNLOAD"
    Error = "ERROR"
    Board = "BOARD"
    BoardError = "BOARDERROR"
    NoBoard = "NOBOARD"
    Ready = "READY"
    IsLogging = "LOGGING"
    GetSessions = "SESSIONS"

    @classmethod
    def composite(cls, base_code, code_id):
        """
        A class method which builds a communication code of more than one part
        such as a download or error command.

        Usage:

            >>> CommunicationCodes.composite(CommunicationCodes.Download, 1)
            "DOWNLOAD 1"
        """
        return base_code + " " + str(code_id)


# commands that are valid to send TO the server
# note only the command up to the space (if there is one) is included
VALID_SERVER_COMMANDS = [
    CommunicationCodes.Start,
    CommunicationCodes.Stop,
    CommunicationCodes.Update,
    CommunicationCodes.Download,
    CommunicationCodes.Board,
    CommunicationCodes.IsLogging,
    CommunicationCodes.GetSessions
]

# commands that are valid to send TO the client
# note only the command up to the space (if there is one) is included
VALID_CLIENT_COMMANDS = [
    CommunicationCodes.Acknowledge,
    CommunicationCodes.Negative,
    CommunicationCodes.InSession,
    CommunicationCodes.NoSession,
    CommunicationCodes.BoardError,
    CommunicationCodes.NoBoard,
    CommunicationCodes.Error,
    CommunicationCodes.Ready
]

MAX_MESSAGE_LENGTH = 112  # max length of message in bits
PAYLOAD_LENGTH = 64  # min length of payload in bits
MESSAGE_BYTE_LENGTH = 28  # number of characters in a hex message string (0-f is 4 bytes)

BOARD_MESSAGE_MAPPING = {
    "sender": {"start": 0, "end": 8},
    "type": {"start": 8, "end": 11},
    "flag1": {"start": 11},
    "flag2": {"start": 12},
    "flag3": {"start": 13},
    "flag4": {"start": 14},
    "flag5": {"start": 15},
    "timestamp": {"start": 16, "end": 48},
    "payload": {"start": 48, "end": -1}
}

SerialUpdatePeriod = 1.0  # serial update period in seconds

SerialCommands = {
    'ACK': '40',
    'TRANSMIT': 'C0',
    'ID': '81'
}
