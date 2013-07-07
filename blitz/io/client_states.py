__author__ = 'Will Hart'

import logging
import threading

from blitz.constants import *


class BaseState(object):
    """
    A base state diagram which provides a few methods - this should not be directly instantiated.

    All methods return a BaseState derived object which should handle future message processing
    """

    logger = logging.getLogger(__name__)

    def enter_state(self, tcp, state):
        """Called when entering the state"""
        self.logger.debug("[TCP] Calling base.enter_state >> " + state.__name__)
        return state()

    def process_message(self, tcp, msg):
        """Called when a message needs processing"""
        self.logger.debug("[TCP] Calling base.process_message: " + msg)
        raise NotImplementedError()

    def send_message(self, tcp, msg):
        """
        Send the passed message over TCP and return the current state
        """
        self.logger.debug("[TCP] Calling base.send_message: " + msg)
        tcp._do_send(msg)
        return self

    def go_to_state(self, tcp, state):
        """
        Transition to a new state and call enter_state on it

        :return: the new state
        """
        self.logger.debug("[TCP] Calling base.go_to_state >> " + state.__name__)
        return state().enter_state(tcp, state)

    def __str__(self):
        return "<" + __name__ + ">"

class ClientInitState(BaseState):
    """
    Handles the client starting up - sends a "logging" query
    to the logger and waits for the response
    """

    def enter_state(self, tcp, state):
        """Send a logging query to the logger"""
        self.logger.debug("[TCP] Calling init.enter_state")
        tcp._do_send(CommunicationCodes.IsLogging)
        return self

    def process_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling init.process_message: " + msg)
        if msg == CommunicationCodes.Acknowledge:
            # logger is logging, transition to LOGGING state
            return self.go_to_state(tcp, ClientLoggingState)
        elif msg == CommunicationCodes.Negative:
            # logger is not logging, go to idle
            return self.go_to_state(tcp, ClientIdleState)
        else:
            # no other messages are acceptable in this state
            raise Exception("Unable to process the given message from InitState: " + msg)


class ClientIdleState(BaseState):
    """
    Handles the client idling, waiting for further commands
    """
    def process_message(self, tcp, msg):
        # no server messages are acceptable in this state
        self.logger.debug("[TCP] Calling idle.process_message: " + msg)
        raise Exception("Received unexpected message in IdleState: " + msg)

    def send_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling idle.send_message: " + msg)
        if msg == CommunicationCodes.Start:
            return self.go_to_state(tcp, ClientStartingState)
        elif msg[0:8] == CommunicationCodes.Download:
            tcp._do_send(msg)
            return self.go_to_state(tcp, ClientDownloadingState)
        else:
            raise Exception("Unknown message for IDLE state - " + msg)


class ClientStartingState(BaseState):
    """Handles logging starting - waits for ACK from server"""
    def enter_state(self, tcp, state):
        self.logger.debug("[TCP] Calling starting.enter_state: " + state.__name__)
        tcp._do_send(CommunicationCodes.Start)
        return self

    def process_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling starting.process_message: " + msg)
        if msg == CommunicationCodes.Acknowledge or msg == CommunicationCodes.InSession:
            return self.go_to_state(tcp, ClientLoggingState)

        return self.go_to_state(tcp, ClientIdleState)


class ClientLoggingState(BaseState):
    """
    Handles the client in logging state - sends periodic status updates
    """
    def enter_state(self, tcp, state):
        """sets up a timer which periodically polls the data logger for updates"""
        self.logger.debug("[TCP] Calling logging.enter_state")
        t = threading.Timer(1.0, self.request_update, args=[tcp])
        t.start()
        return self

    def request_update(self, tcp):
        """called on timer tick to request an update from the TCP server"""
        self.logger.critical("TICK")
        tcp.request_update()

        # if we are still logging, request another update
        if type(tcp.current_state) is ClientLoggingState:
            t = threading.Timer(1.0, self.request_update, args=[tcp])
            t.start()

    def send_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling logging.send_message: " + msg)

        # check if we have requested logging to stop
        if msg == CommunicationCodes.Stop:
            return self.go_to_state(tcp, ClientStoppingState)

        # if not, are we requesting a status?
        if msg == CommunicationCodes.Update:
            tcp._do_send(CommunicationCodes.Update)
        elif len(msg) == COMMAND_MESSAGE_BYTES or len(msg) == SHORT_COMMAND_MESSAGE_BYTES:
            # this is likely to be a data message
            tcp.parse_reading(msg)
        else:
            # otherwise we just send the message and let the server sort it out
            tcp._do_send(msg)
        return self


class ClientStoppingState(BaseState):
    """
    Handles waiting for acknowledgement from a client before entering IDLE state
    """
    def enter_state(self, tcp, state):
        self.logger.debug("[TCP] Calling stopping.enter_state: " + state.__name__)
        tcp._do_send(CommunicationCodes.Stop)
        return self

    def process_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling stopping.process_message: " + msg)
        if msg == CommunicationCodes.Acknowledge:
            return self.go_to_state(tcp, ClientIdleState)
        return self


class ClientDownloadingState(BaseState):
    """
    Handles the client in logging state - sends periodic status updates
    """
    def process_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling downloading.process_message: " + msg)
        if msg == CommunicationCodes.Negative:
            # the data has been received
            self.send_message(tcp, CommunicationCodes.Acknowledge)
            return self.go_to_state(tcp, ClientIdleState)

        # otherwise we save the data row for processing
        tcp.parse_reading(msg)
        return self

    def go_to_state(self, tcp, state):
        self.logger.debug("[TCP] Calling downloading.go_to_state >> " + state.__name__)
        if type(state) == ClientIdleState:
            tcp._do_send(CommunicationCodes.Acknowledge) # acknowledge end of download recieved

        return super(ClientDownloadingState, self).go_to_state(tcp, state)
