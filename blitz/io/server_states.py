__author__ = 'Will Hart'

from blitz.constants import *
from blitz.io.client_states import BaseState


def validate_command(tcp, msg, commands):
    """
    Helper function which checks to see if a message is in the list of valid commands
    and sends an appropriate response over the TCP network
    """
    if msg.split(' ')[0] not in commands:
        tcp.send("ERROR 2")
    else:
        tcp.send("ERROR 1")


class ServerIdleState(BaseState):

    def enter_state(self, tcp, state):
        print "Calling ServerIdleState.enter_state: " + state.__name__
        tcp.send("READY")
        return self

    def process_message(self, tcp, msg):
        """
        Handle the various requests from the client including to start and stop logging
        """

        print "Calling ServerIdleState.process_message: " + msg
        # check if it is a command which causes a change of state
        if msg == "START":
            tcp.send("ACK")
            return self.go_to_state(tcp, ServerLoggingState)
        elif msg[0:8] == "DOWNLOAD":
            return self.go_to_state(tcp, ServerDownloadingState)

        if msg == "STOP" or msg == "STATUS":
            # huh? We are not logging!?
            tcp.send("NOSESSION")
        else:
            validate_command(tcp, msg, VALID_SERVER_COMMANDS)

        return self


class ServerLoggingState(BaseState):

    def enter_state(self, tcp, state):
        print "Calling ServerLoggingState.enter_state: " + state.__name__

        # TODO raise signal to start logging
        print "[SIGNAL] Start logging"

        return self

    def process_message(self, tcp, msg):
        print "Calling ServerLoggingState.process_message: " + msg

        if msg == "STOP":

            # TODO raise signal to stop logging
            print "[SIGNAL] Stop logging"
            tcp.send("ACK")
            return self.go_to_state(tcp, ServerIdleState)

        if msg == "STATUS":
            # TODO raise signal to send status
            print "[SIGNAL] send status"

        else:
            validate_command(tcp, msg, VALID_SERVER_COMMANDS)

        return self


class ServerDownloadingState(BaseState):
    def download_complete(self, tcp):
        print "Calling ServerLoggingState.download_complete"
        return self.go_to_state(tcp, ServerIdleState)

    def process_message(self, tcp, msg):
        validate_command(tcp, msg, VALID_SERVER_COMMANDS)
        return self


class ServerClosedState(BaseState):
    def process_message(self, tcp, msg):
        print "Calling ServerClosedState.process_message" + msg
        raise Exception("Attempted to receive message on closed server" + msg)

    def send_message(self, tcp, msg):
        print "Calling ServerClosedState.send_message" + msg
        raise Exception("Attempted to send message on closed server" + msg)
