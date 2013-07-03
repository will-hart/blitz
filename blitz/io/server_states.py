__author__ = 'Will Hart'

from blitz.constants import *
from blitz.io.client_states import BaseState
from blitz.utilities import generate_tcp_server_fixtures


def validate_command(msg, commands):
    """
    Helper function which checks to see if a message is in the list of valid commands
    and sends an appropriate response over the TCP network
    """
    if msg.split(' ')[0] in commands:
        return CommunicationCodes.composite(CommunicationCodes.Error, 1)
    else:
        return CommunicationCodes.composite(CommunicationCodes.Error, 2)


class ServerIdleState(BaseState):

    def enter_state(self, tcp, state):
        self.logger.debug("[TCP] Calling ServerIdleState.enter_state: " + state.__name__)
        tcp._send(CommunicationCodes.Ready)
        return self

    def process_message(self, tcp, msg):
        """
        Handle the various requests from the client including to start and stop logging
        """

        self.logger.debug("[TCP] Calling ServerIdleState.process_message: " + msg)
        # check if it is a command which causes a change of state
        if msg == CommunicationCodes.Start:
            tcp._send(CommunicationCodes.Acknowledge)
            return self.go_to_state(tcp, ServerLoggingState)
        elif msg[0:8] == CommunicationCodes.Download:
            return self.go_to_state(tcp, ServerDownloadingState)

        if msg == CommunicationCodes.Stop or msg == CommunicationCodes.Update:
            # huh? We are not logging!?
            tcp._send(CommunicationCodes.NoSession)
        else:
            tcp._send(validate_command(msg, VALID_SERVER_COMMANDS))

        return self


class ServerLoggingState(BaseState):

    def enter_state(self, tcp, state):
        self.logger.debug("[TCP] Calling ServerLoggingState.enter_state: " + state.__name__)

        # TODO raise signal to start logging
        self.logger.debug("[TCP] [SIGNAL] Start logging")

        return self

    def process_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling ServerLoggingState.process_message: " + msg)

        if msg == CommunicationCodes.Stop:
            # TODO raise signal to stop logging
            self.logger.debug("[TCP] [SIGNAL] Stop logging")
            tcp._send(CommunicationCodes.Acknowledge)
            return self.go_to_state(tcp, ServerIdleState)

        if msg == CommunicationCodes.Update:
            # TODO raise signal to send status
            self.logger.debug("[TCP] [SIGNAL] send status")

            # TODO replace with REAL data :)
            fixture = generate_tcp_server_fixtures()
            tcp._send(fixture.hex)

        elif msg == CommunicationCodes.Start:
            tcp._send(CommunicationCodes.InSession)
        else:
            tcp._send(validate_command(msg, VALID_SERVER_COMMANDS))

        return self


class ServerDownloadingState(BaseState):
    def download_complete(self, tcp):
        self.logger.debug("[TCP] Calling ServerLoggingState.download_complete")
        return self.go_to_state(tcp, ServerIdleState)

    def process_message(self, tcp, msg):
        tcp._send(validate_command(msg, VALID_SERVER_COMMANDS))
        return self


class ServerClosedState(BaseState):
    def process_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling ServerClosedState.process_message" + msg)
        raise Exception("Attempted to receive message on closed server" + msg)

    def send_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling ServerClosedState.send_message" + msg)
        raise Exception("Attempted to send message on closed server" + msg)
