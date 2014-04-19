__author__ = 'Will Hart'

import logging
import threading
import time

from blitz.constants import *
import blitz.communications.signals as sigs


class BaseState(object):
    """
    A base state diagram which provides a few methods - this should not be directly instantiated.

    All methods return a BaseState derived object which should handle future message processing
    """

    logger = logging.getLogger(__name__)

    def enter_state(self, tcp, state, args=None):
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
        self.logger.debug("[TCP] Calling base.send_message: " + str(msg))
        tcp.do_send(msg)
        return self

    def go_to_state(self, tcp, state, args=None):
        """
        Transition to a new state and call enter_state on it

        :return: the new state
        """
        self.logger.debug("[TCP] Calling base.go_to_state >> " + state.__name__)
        return state().enter_state(tcp, state, args)

    def __str__(self):
        return "<" + self.__name__ + ">"


class ClientInitState(BaseState):
    """
    Handles the client starting up - sends a "logging" query
    to the logger and waits for the response
    """
    __name__ = "ClientInitState"

    def enter_state(self, tcp, state, args=None):
        """Send a logging query to the logger"""
        self.logger.debug("[TCP] Calling init.enter_state")
        tcp.do_send(CommunicationCodes.IsLogging)
        return self

    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling init.receive_message: " + msg)
        sigs.process_finished.send()

        if msg == CommunicationCodes.Acknowledge:
            # logger is logging, transition to LOGGING state
            return self.go_to_state(tcp, ClientLoggingState)
        elif msg == CommunicationCodes.Negative:
            # logger is not logging, go to idle
            return self.go_to_state(tcp, ClientIdleState)
        elif msg[0:5] == CommunicationCodes.Error:
            sigs.logger_error_received.send(msg)
            return self
        else:
            if msg == "":
                self.logger.warning("Received empty message, ignoring")
                return self
            else:
                # no other messages are acceptable in this state
                raise Exception("Unable to process the given message from InitState: " + msg)


class ClientIdleState(BaseState):
    """
    Handles the client idling, waiting for further commands
    """
    __name__ = "ClientIdleState"

    def receive_message(self, tcp, msg):
        # only ACK is acceptable in this state
        if msg[0:6] == CommunicationCodes.Boards:
            sigs.board_list_received.send(msg)
            return self
        if msg == CommunicationCodes.Acknowledge:
            sigs.process_finished.send()
            return self

        self.logger.warning("[TCP] Calling idle.receive_message: " + msg)
        return self

    def send_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling idle.send_message: " + msg)
        if msg == CommunicationCodes.Start:
            return self.go_to_state(tcp, ClientStartingState)
        elif msg == CommunicationCodes.GetSessions:
            return self.go_to_state(tcp, ClientSessionListState)
        elif msg[0:8] == CommunicationCodes.Download:
            tcp.do_send(msg)
            new_state = self.go_to_state(tcp, ClientDownloadingState, int(msg.split(" ")[1]))
            return new_state
        elif msg[0:5] == CommunicationCodes.Board:
            tcp.do_send(msg)
        elif msg[0:5] == CommunicationCodes.Reset:
            self.logger.warning("[TCP] Forcing logger reset")
            tcp.do_send(msg)
            return self.go_to_state(tcp, ClientIdleState)
        elif msg[0:6] == CommunicationCodes.Delete:
            tcp.do_send(msg)
        else:
            self.logger.error("Attempted to send unknown message for IDLE state: {0}".format(msg))
            raise Exception("Unknown message for IDLE state - " + msg)

        return self


class ClientSessionListState(BaseState):

    sessions = []
    __name__ = "ClientSessionListState"

    def enter_state(self, tcp, state, args=None):
        """Send a logging session list to the logger"""
        self.sessions = []
        self.logger.debug("[TCP] Calling session_list.enter_state")
        sigs.process_started.send("Downloading session data from the logger")
        tcp.do_send(CommunicationCodes.GetSessions)
        return self

    def receive_message(self, tcp, msg):

        parts = msg.split("\n")
        delimiter = parts[-1]
        parts = parts[:-1]

        if delimiter != CommunicationCodes.Negative:
            self.logger.info("Ignoring session list message with incorrect format [%s]" % msg)
            self.go_to_state(tcp, ClientIdleState)
            return self

        # process a session message
        for part in parts:
            msg_parts = part.split(" ")
            if len(msg_parts) == 4:
                self.sessions.append(msg_parts)
                self.logger.debug("Parsed session list message [%s:%s:%s:%s]" % (
                    msg_parts[0], msg_parts[1], msg_parts[2], msg_parts[3]))
        return self.go_to_state(self, ClientIdleState)

    def go_to_state(self, tcp, state, args=None):
        """
        sends a signal to save the session list to database, and then calls super go_to_state
        """
        sigs.process_finished.send()
        sigs.client_session_list_updated.send(self.sessions)
        return super(ClientSessionListState, self).go_to_state(tcp, state)


class ClientStartingState(BaseState):
    """Handles logging starting - waits for ACK from server"""
    __name__ = "ClientStartingState"

    def enter_state(self, tcp, state, args=None):
        self.logger.debug("[TCP] Calling starting.enter_state: " + state.__name__)
        tcp.do_send(CommunicationCodes.Start)
        return self

    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling starting.receive_message: " + msg)
        sigs.process_finished.send()

        if msg == CommunicationCodes.Acknowledge or msg == CommunicationCodes.InSession:
            return self.go_to_state(tcp, ClientLoggingState)
        elif msg[0:5] == CommunicationCodes.Error:
            sigs.logger_error_received.send(msg)

        return self.go_to_state(tcp, ClientIdleState)


class ClientLoggingState(BaseState):
    """
    Handles the client in logging state - sends periodic status updates
    """

    __name__ = "ClientLoggingState"

    def enter_state(self, tcp, state, args=None):
        """sets up a timer which periodically polls the data logger for updates"""
        sigs.logging_started.send()
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
            time.sleep(1.0)  # TODO get this value from config
        self.logger.info("Stopping update request thread on TcpClient")

    def send_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling logging.send_message: " + msg)

        # check if we have requested logging to stop
        if msg == CommunicationCodes.Stop:
            return self.go_to_state(tcp, ClientStoppingState)

        # if not, are we requesting a status?
        if msg == CommunicationCodes.Update:
            tcp.do_send(CommunicationCodes.Update)

        elif msg[0:5] == CommunicationCodes.Board:
            tcp.do_send(msg)
            return self

        else:
            # otherwise we just send the message and let the server sort it out
            tcp.do_send(msg)
        return self

    def receive_message(self, tcp, msg):
        if len(msg) == 4 or len(msg) >= 28:
            sigs.cache_line_received.send(msg)
        else:
            if len(msg) >= 5 and msg[0:5] == CommunicationCodes.Error:
                self.logger.error("Received error code from logger [%s], stopping logging" % msg)
                return self.go_to_state(tcp, ClientStoppingState)
            elif msg != CommunicationCodes.Acknowledge:
                self.logger.warning("Ignoring unknown message [%s] in logging state" % msg)

        return self

    def go_to_state(self, tcp, state, args=None):
        self.logger.debug("[TCP] Calling logging.go_to_state: " + state.__name__)
        self.__stop_updater.set()
        self.update_thread.join()
        return super(ClientLoggingState, self).go_to_state(tcp, state)


class ClientStoppingState(BaseState):
    """
    Handles waiting for acknowledgement from a client before entering IDLE state
    """

    __name__ = "ClientStoppingState"

    def enter_state(self, tcp, state, args=None):
        self.logger.debug("[TCP] Calling stopping.enter_state: " + state.__name__)
        tcp.do_send(CommunicationCodes.Stop)
        return self

    def receive_message(self, tcp, msg):
        self.logger.debug("[TCP] Calling stopping.receive_message: " + msg)
        sigs.process_finished.send()

        if msg == CommunicationCodes.Acknowledge:
            sigs.logging_stopped.send()
            return self.go_to_state(tcp, ClientSessionListState)
        return self


class ClientDownloadingState(BaseState):
    """
    Handles the client in logging state - sends periodic status updates
    """

    __name__ = "ClientDownloadingState"

    session_id = 0

    def enter_state(self, tcp, state, session_id=None):
        self.logger.debug("[TCP] Calling downloading.enter_state with session ID " + str(session_id))
        self.session_id = session_id
        return self

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

        elif msg[0:5] == CommunicationCodes.Error:
            tcp.send(CommunicationCodes.Reset)
            self.logger.warning("Error on download, forcing server to transition to idle state")
            return self.go_to_state(tcp, ClientIdleState)

        # and then request the next dump from the server
        tcp.send(CommunicationCodes.Acknowledge)
        return self

    def go_to_state(self, tcp, state, args=None):
        sigs.process_finished.send()
        self.logger.debug("[TCP] Calling downloading.go_to_state >> " + state.__name__)
        return super(ClientDownloadingState, self).go_to_state(tcp, state)
