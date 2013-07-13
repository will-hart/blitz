__author__ = 'Will Hart'

import logging
import threading
import time

from blitz.constants import *
import blitz.io.signals as sigs


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

    def receive_message(self, tcp, msg):
        """Called when a message needs processing"""
        self.logger.debug("[TCP] Calling base.receive_message: " + msg)
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

    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling init.receive_message: " + msg)
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
    def receive_message(self, tcp, msg):
        # no server messages are acceptable in this state
        self.logger.debug("[TCP] Calling idle.receive_message: " + msg)
        raise Exception("Received unexpected message in IdleState: " + msg)

    def send_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling idle.send_message: " + msg)
        if msg == CommunicationCodes.Start:
            return self.go_to_state(tcp, ClientStartingState)
        elif msg == CommunicationCodes.GetSessions:
            return self.go_to_state(tcp, ClientSessionListState)
        elif msg[0:8] == CommunicationCodes.Download:
            tcp._do_send(msg)
            new_state = self.go_to_state(tcp, ClientDownloadingState)
            new_state.session_id = int(msg.split(" ")[1])
            return new_state
        else:
            raise Exception("Unknown message for IDLE state - " + msg)


class ClientSessionListState(BaseState):

    sessions = []

    def enter_state(self, tcp, state):
        """Send a logging session list to the logger"""
        self.sessions = []
        self.logger.debug("[TCP] Calling session_list.enter_state")
        tcp._do_send(CommunicationCodes.GetSessions)
        return self

    def receive_message(self, tcp, msg):

        parts = msg.split("\n")
        delimiter = parts[len(parts) - 1]
        parts = parts[:-1]

        if delimiter != CommunicationCodes.Negative:
            self.logger.info("Ignoring session list message with incorrect format [%s]" % msg)

            # todo there is the potential to get stuck in "sessionList" state here if the first response is malformed
            return self

        # process a session message
        for part in parts:
            msg_parts = part.split(" ")
            if len(msg_parts) == 4:
                self.sessions.append(msg_parts)
                self.logger.debug("Parsed session list message [%s:%s:%s:%s]" % (
                    msg_parts[0], msg_parts[1], msg_parts[2], msg_parts[3]))
        return self.go_to_state(self, ClientIdleState)

    def go_to_state(self, tcp, state):
        """
        sends a signal to save the session list to database, and then calls super go_to_state
        """
        sigs.client_session_list_updated.send(self.sessions)
        return super(ClientSessionListState, self).go_to_state(tcp, state)


class ClientStartingState(BaseState):
    """Handles logging starting - waits for ACK from server"""
    def enter_state(self, tcp, state):
        self.logger.debug("[TCP] Calling starting.enter_state: " + state.__name__)
        tcp._do_send(CommunicationCodes.Start)
        return self

    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling starting.receive_message: " + msg)
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
        self.__stop_updater = threading.Event()
        self.update_thread = threading.Thread(target=self.request_update, args=[self.__stop_updater, tcp])
        self.update_thread.daemon = True
        self.update_thread.start()
        return self

    def request_update(self, stop_event, tcp):
        """called on timer tick to request an update from the TCP server"""
        while not stop_event.is_set():
            tcp.send(CommunicationCodes.Update)
            time.sleep(2.0)  # TODO get this value from config
        self.logger.info("Stopping update request thread on TcpClient")

    def send_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling logging.send_message: " + msg)

        # check if we have requested logging to stop
        if msg == CommunicationCodes.Stop:
            return self.go_to_state(tcp, ClientStoppingState)

        # if not, are we requesting a status?
        if msg == CommunicationCodes.Update:
            tcp._do_send(CommunicationCodes.Update)
        else:
            # otherwise we just send the message and let the server sort it out
            tcp._do_send(msg)
        return self

    def receive_message(self, tcp, msg):
        if len(msg) == 4 or len(msg) >= 28:
            sigs.cache_line_received.send(msg)
        else:
            self.logger.warning("Received message of unexpected length: " + msg)
        return self

    def go_to_state(self, tcp, state):
        self.logger.debug("[TCP] Calling logging.go_to_state: " + state.__name__)
        self.__stop_updater.set()
        self.update_thread.join()
        return super(ClientLoggingState, self).go_to_state(tcp, state)


class ClientStoppingState(BaseState):
    """
    Handles waiting for acknowledgement from a client before entering IDLE state
    """
    def enter_state(self, tcp, state):
        self.logger.debug("[TCP] Calling stopping.enter_state: " + state.__name__)
        tcp._do_send(CommunicationCodes.Stop)
        return self

    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling stopping.receive_message: " + msg)
        if msg == CommunicationCodes.Acknowledge:
            return self.go_to_state(tcp, ClientSessionListState)
        return self


class ClientDownloadingState(BaseState):
    """
    Handles the client in logging state - sends periodic status updates
    """

    session_id = -1

    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling downloading.receive_message: " + msg)

        # removing the command message and send the remainder off for processing via a signal
        msg_parts = msg.split("\n")
        if msg_parts[-1][0:2] != "0x":
            del msg_parts[-1]

        sigs.data_line_received.send((msg_parts, self.session_id))

        if msg[-4:] == CommunicationCodes.Negative:
            # the data has been received
            return self.go_to_state(tcp, ClientIdleState)
        # and then request the next dump from the server
        tcp.send(CommunicationCodes.Acknowledge)
        return self

    def go_to_state(self, tcp, state):
        self.logger.debug("[TCP] Calling downloading.go_to_state >> " + state.__name__)
        if type(state) == ClientIdleState:
            tcp._do_send(CommunicationCodes.Acknowledge)  # acknowledge end of download received

        return super(ClientDownloadingState, self).go_to_state(tcp, state)
