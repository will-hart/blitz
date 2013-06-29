__author__ = 'Will Hart'

from blitz.constants import *

class BaseState(object):
    """
    A base state diagram which provides a few methods - this should not be directly instantiated.

    All methods return a BaseState derived object which should handle future message processing
    """

    def enter_state(self, tcp, state):
        """Called when entering the state"""
        print "Calling base.enter_state >> " + state.__name__
        return state()

    def process_message(self, tcp, msg):
        """Called when a message needs processing"""
        print "Calling base.process_message: " + msg
        raise NotImplementedError()

    def send_message(self, tcp, msg):
        """
        Send the passed message over TCP and return the current state
        """
        print "Calling base.send_message: " + msg
        tcp.send(msg)
        return self

    def go_to_state(self, tcp, state):
        """
        Transition to a new state and call enter_state on it

        :return: the new state
        """
        print "Calling base.go_to_state >> " + state.__name__
        return state().enter_state(tcp, state)

    def __str__(self):
        return "<" + __name__ + ">"

class InitState(BaseState):
    """
    Handles the client starting up - sends a "logging" query
    to the logger and waits for the response
    """

    def enter_state(self, tcp, state):
        """Send a logging query to the logger"""
        print "Calling init.enter_state"
        return self.send_message(tcp, "LOGGING")

    def process_message(self, tcp, msg):
        print "Calling init.process_message: " + msg
        if msg == "ACK":
            # logger is logging, transition to LOGGING state
            return self.go_to_state(tcp, LoggingState)
        elif msg == "NACK":
            # logger is not logging, go to idle
            return self.go_to_state(tcp, IdleState)
        else:
            # no other messages are acceptable in this state
            raise Exception("Unable to process the given message from InitState: " + msg)


class IdleState(BaseState):
    """
    Handles the client idling, waiting for further commands
    """
    def process_message(self, tcp, msg):
        # no server messages are acceptable in this state
        print "Calling idle.process_message: " + msg
        raise Exception("Received unexpected message in IdleState: " + msg)

    def send_message(self, tcp, msg):
        print "Calling idle.send_message: " + msg
        if msg == "START":
            tcp.send(msg)
            return self.go_to_state(tcp, StartingState)
        elif msg[0:8] == "DOWNLOAD":
            tcp.send(msg)
            return self.go_to_state(tcp, DownloadingState)
        else:
            raise Exception("Unknown message for IDLE state - " + msg)


class StartingState(BaseState):
    """Handles logging starting - waits for ACK from server"""
    def process_message(self, tcp, msg):
        print "Calling starting.process_message: " + msg
        if msg == "ACK":
            return self.go_to_state(tcp, LoggingState)


class LoggingState(BaseState):
    """
    Handles the client in logging state - sends periodic status updates
    """
    def send_message(self, tcp, msg):
        print "Calling logging.send_message: " + msg

        # check if we have requested logging to stop
        if msg == "STOP":
            tcp.send("STOP")
            return self.go_to_state(tcp, StoppingState)

        # if not, are we requesting a status?
        if msg == "STATUS":
            tcp.send("STATUS")
        elif len(msg) == COMMAND_MESSAGE_BYTES or len(msg) == SHORT_COMMAND_MESSAGE_BYTES:
            # this is likely to be a data message
            tcp.parse_reading(msg)
        else:
            # otherwise we just send the message and let the server sort it out
            tcp.send(msg)
        return self


class StoppingState(BaseState):
    """
    Handles waiting for acknowledgement from a client before entering IDLE state
    """
    def process_message(self, tcp, msg):
        print "Calling stopping.process_message: " + msg
        if msg == "ACK":
            return self.go_to_state(tcp, IdleState)
        return self


class DownloadingState(BaseState):
    """
    Handles the client in logging state - sends periodic status updates
    """
    def process_message(self, tcp, msg):
        print "Calling downloading.process_message: " + msg
        if msg == "NACK":
            # the data has been received
            self.send_message(tcp, "ACK")
            return self.go_to_state(tcp, IdleState)

        # otherwise we save the data row for processing
        tcp.parse_reading(msg)
        return self

    def go_to_state(self, tcp, state):
        print "Calling downloading.go_to_state >> " + state.__name__
        if type(state) == IdleState:
            tcp.send("ACK") # acknowledge end of download recieved

        return super(DownloadingState, self).go_to_state(tcp, state)