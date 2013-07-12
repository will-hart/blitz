__author__ = 'Will Hart'

from blitz.constants import *
from blitz.io.client_states import BaseState
import blitz.io.signals as sigs
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
        return self

    def receive_message(self, tcp, msg):
        """
        Handle the various requests from the client including to start and stop logging
        """
        self.logger.debug("[TCP] Calling ServerIdleState.receive_message: " + msg)
        # check if it is a command which causes a change of state
        if msg == CommunicationCodes.Start:
            tcp._do_send(CommunicationCodes.Acknowledge)
            return self.go_to_state(tcp, ServerLoggingState)
        elif msg == CommunicationCodes.GetSessions:
            sigs.client_requested_session_list.send()
            return self
        elif msg[0:8] == CommunicationCodes.Download:
            msg_parts = msg.split(" ")
            if len(msg_parts) != 2:
                tcp.send(CommunicationCodes.Negative)
                return self

            sigs.client_requested_download.send(int(msg_parts[1]))
            return self.go_to_state(tcp, ServerDownloadingState)

        if msg == CommunicationCodes.Stop or msg == CommunicationCodes.Update:
            # huh? We are not logging!?
            tcp._do_send(CommunicationCodes.NoSession)
        elif msg == CommunicationCodes.IsLogging:
            tcp._do_send(CommunicationCodes.Negative)
        else:
            tcp._do_send(validate_command(msg, VALID_SERVER_COMMANDS))

        return self


class ServerLoggingState(BaseState):

    def enter_state(self, tcp, state):
        self.logger.debug("[TCP] Calling ServerLoggingState.enter_state: " + state.__name__)
        sigs.logging_started.send()
        return self

    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling ServerLoggingState.receive_message: " + msg)

        if msg == CommunicationCodes.Stop:
            sigs.logging_stopped.send()
            self.logger.debug("[TCP] [SIGNAL] Stop logging")
            tcp._do_send(CommunicationCodes.Acknowledge)
            return self.go_to_state(tcp, ServerIdleState)

        if msg == CommunicationCodes.Update:
            sigs.client_status_request.send(tcp)

            # TODO replace with REAL data :)
            fixture = generate_tcp_server_fixtures()
            tcp._do_send("0x" + fixture.hex)

        elif msg == CommunicationCodes.Start:
            tcp._do_send(CommunicationCodes.InSession)
        elif msg == CommunicationCodes.IsLogging:
            tcp._do_send(CommunicationCodes.Negative)

        else:
            tcp._do_send(validate_command(msg, VALID_SERVER_COMMANDS))

        return self


class ServerDownloadingState(BaseState):

    def send_message(self, tcp, msg):

        # blindly send everything
        tcp._do_send(msg)

        # check if that was the last message (i.e. last four characters are NACK
        if msg[-4:] == CommunicationCodes.Negative:
            return self.go_to_state(tcp, ServerIdleState)

        return self

    def receive_message(self, tcp, msg):
        # ACK signifies part message received and server should continue sending.
        # All other messages are in error
        if msg != CommunicationCodes.Acknowledge:
            tcp._do_send(validate_command(msg, VALID_SERVER_COMMANDS))
        return self


class ServerClosedState(BaseState):
    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling ServerClosedState.receive_message" + msg)
        raise Exception("Attempted to receive message on closed server" + msg)

    def send_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling ServerClosedState.send_message" + msg)
        raise Exception("Attempted to send message on closed server" + msg)
