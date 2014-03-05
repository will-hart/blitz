__author__ = 'Will Hart'

from blitz.constants import *
from blitz.communications.client_states import BaseState
import blitz.communications.signals as sigs


def validate_command(msg, commands):
    """
    Helper function which checks to see if a message is in the list of valid commands
    and sends an appropriate response over the TCP network
    """
    if msg.split(' ')[0] in commands:
        return CommunicationCodes.composite(CommunicationCodes.Error, 1)
    else:
        return CommunicationCodes.composite(CommunicationCodes.Error, 2)


class ServerBaseState(BaseState):
    """
    A server base state which also implements commands that can be
    received in all states such as BOARD commands
    """

    def process_standard_messages(self, tcp, msg):
        """
        Processes standard messages that can be handled in any state

        :returns: True if the message was handled here, False if it was not
        """
        if msg[0:5] == CommunicationCodes.Board:
            sigs.board_command_received.send(msg.split(" ")[1:])
            tcp.send(CommunicationCodes.Acknowledge)
            return True

        return False  # message was not handled


class ServerIdleState(ServerBaseState):

    def enter_state(self, tcp, state, args=None):
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

            return self.go_to_state(tcp, ServerDownloadingState, msg_parts[1])
        elif msg[0:5] == CommunicationCodes.Reset:
            return self
        elif msg == CommunicationCodes.Stop or msg == CommunicationCodes.Update:
            # huh? We are not logging!?
            tcp._do_send(CommunicationCodes.NoSession)
        elif msg == CommunicationCodes.IsLogging:
            self.logger.debug("Responding with NACK, server not currently logging")
            tcp._do_send(CommunicationCodes.Negative)
        elif not self.process_standard_messages(tcp, msg):
            tcp._do_send(validate_command(msg, VALID_SERVER_COMMANDS))

        return self


class ServerLoggingState(ServerBaseState):

    def enter_state(self, tcp, state, args=None):
        self.logger.debug("[TCP] Calling ServerLoggingState.enter_state: " + state.__name__)
        sigs.logging_started.send(tcp)
        return self

    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling ServerLoggingState.receive_message: " + msg)

        if msg == CommunicationCodes.Stop:
            self.logger.debug("[TCP] [SIGNAL] Stop logging")
            tcp._do_send(CommunicationCodes.Acknowledge)
            sigs.logging_stopped.send()
            return self.go_to_state(tcp, ServerIdleState)

        if msg == CommunicationCodes.Update:
            sigs.server_status_request.send(tcp)

        elif msg == CommunicationCodes.Start:
            tcp._do_send(CommunicationCodes.InSession)

        elif msg == CommunicationCodes.IsLogging:
            self.logger.debug("Responding with ACK, server is currently logging")
            tcp._do_send(CommunicationCodes.Acknowledge)

        elif msg[0:5] == CommunicationCodes.Reset:
            return self.go_to_state(tcp, ServerIdleState)

        elif not self.process_standard_messages(tcp, msg):
            tcp._do_send(validate_command(msg, VALID_SERVER_COMMANDS))

        return self


class ServerDownloadingState(ServerBaseState):

    session_data = []
    send_index = 0

    def enter_state(self, tcp, state, session_id=None):
        self.logger.debug("[TCP] Calling ServerDownloadingState.enter_state")

        self.send_index = 0
        self.session_data = []
        sigs.client_requested_download.send(session_id)
        return self

    def send_message(self, tcp, msg):

        self.logger.debug("[TCP] Calling ServerDownloadingState.send_message")

        if msg is not None:
            # this is the first send request, send the first 100 lines
            self.send_index = 0
            self.session_data = msg

        elif len(self.session_data) == 0:
            # no data to send
            tcp._do_send(CommunicationCodes.Negative)
            return self.go_to_state(tcp, ServerIdleState)

        # send the next block of messages, appending the correct command code
        #  >> ACK for more to come
        #  >> NACK for transmission complete
        lines = "\n".join(self.session_data[self.send_index])
        self.send_index += 1

        if self.send_index == len(self.session_data):
            lines += "\n" + CommunicationCodes.Negative
            tcp._do_send(lines)
            self.session_data = []
            self.send_index = 0
            return self.go_to_state(tcp, ServerIdleState)

        lines += "\n" + CommunicationCodes.Acknowledge
        tcp._do_send(lines)
        return self

    def receive_message(self, tcp, msg):

        self.logger.debug("[TCP] Calling ServerDownloadingState.receive_message")

        # ACK signifies part message received and server should continue sending.
        # All other messages are in error
        if msg == CommunicationCodes.Acknowledge:
            self.logger.debug("[TCP] Sending next download part")
            self.send_message(tcp, None)

        elif msg[0:5] == CommunicationCodes.Reset:
            return self.go_to_state(tcp, ServerIdleState)

        elif not self.process_standard_messages(tcp, msg):
            self.logger.warning("[TCP] Unknown message received in download state - " + msg)
            tcp._do_send(validate_command(msg, VALID_SERVER_COMMANDS))

        return self


class ServerClosedState(ServerBaseState):
    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling ServerClosedState.receive_message" + msg)

        if self.process_standard_messages(tcp, msg):
            return self
        else:
            raise Exception("Attempted to receive message on closed server" + msg)

    def send_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling ServerClosedState.send_message" + msg)
        raise Exception("Attempted to send message on closed server" + msg)
