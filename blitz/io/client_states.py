__author__ = 'Will Hart'


class BaseState(object):
    """
    A base state diagram which provides a few methods - this should not be directly instantiated.

    All methods return a BaseState derived object which should handle future message processing
    """

    def EnterState(self, tcp):
        """Called when entering the state"""
        return self

    def ProcessMessage(self, tcp, msg):
        """Called when a message needs processing"""
        return self

    def SendMessage(self, tcp, msg):
        """
        Send the passed message over TCP and return the current state
        """
        tcp.send(msg)
        return self

    def GoToState(self, tcp, state):
        """
        Transition to a new state and call EnterState on it

        :return: the new state
        """
        return state().EnterState(tcp)


class InitState(BaseState):
    """
    Handles the client starting up - sends a "logging" query
    to the logger and waits for the response
    """

    def EnterState(self, tcp):
        """Send a logging query to the logger"""
        return self.SendMessage(tcp, "LOGGING")

    def ProcessMessage(self, tcp, msg):
        if msg == "ACK":
            # logger is logging, transition to LOGGING state
            return self.GoToState(tcp, LoggingState)
        elif msg == "NACK":
            # logger is not logging, go to idle
            return self.GoToState(tcp, IdleState)
        else:
            # no other messages are acceptable in this state
            raise Exception("Unable to process the given message from InitState: " + msg)


class IdleState(BaseState):
    """
    Handles the client idling, waiting for further commands
    """
    def ProcessMessage(self, tcp, msg):
        # no server messages are acceptable in this state
        raise Exception("Received unexpected message in IdleState: " + msg)

    def SendMessage(self, tcp, msg):
        if msg == "START":
            tcp.send(msg)
            return self.GoToState(tcp, StartingState)
        elif msg[0:8] == "DOWNLOAD":
            tcp.send(msg)
            return self.GoToState(tcp, DownloadingState)
        else:
            raise Exception("Unknown message for IDLE state - " + msg)


class StartingState(BaseState):
    """Handles logging starting - waits for ACK from server"""
    def ProcessMessage(self, tcp, msg):
        if msg == "ACK":
            return self.GoToState(tcp, LoggingState)


class LoggingState(BaseState):
    """
    Handles the client in logging state - sends periodic status updates
    """
    def SendMessage(self, tcp, msg):
        if msg == "STOP":
            tcp.send("STOP")
            return self.GoToState(tcp, StoppingState)
        elif msg == "STATUS":
            tcp.send("STATUS")
            return self.GoToState(tcp, DownloadingState)
        return self


class StoppingState(BaseState):
    """
    Handles waiting for acknowledgement from a client before entering IDLE state
    """
    def ProcessMessage(self, tcp, msg):
        if msg == "ACK":
            return self.GoToState(tcp, IdleState)
        return self


class DownloadingState(BaseState):
    """
    Handles the client in logging state - sends periodic status updates
    """
    def ProcessMessage(self, tcp, msg):
        if msg == "NACK":
            # the data has been received
            self.SendMessage(tcp, "ACK")
            return self.GoToState(tcp, IdleState)

        # otherwise we save the data row for processing
        tcp.ParseReading(msg)
        return self

