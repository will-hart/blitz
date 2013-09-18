class BlitzGuiMixin(object):
    def connect_to_logger(self):
        """
        Connects the application to the data logger via a TCP connection
        """
        self.connect_action.setEnabled(False)
        self.disconnect_action.setEnabled(True)
        self.start_session_action.setEnabled(True)
        self.stop_session_action.setEnabled(False)
        self.status_bar.showMessage("Connected to logger")

    def disconnect_from_logger(self):
        """
        Disconnects the application from the data logger
        """
        self.connect_action.setEnabled(True)
        self.disconnect_action.setEnabled(False)
        self.start_session_action.setEnabled(False)
        self.stop_session_action.setEnabled(False)
        self.status_bar.showMessage("Disconnected from logger")

    def start_session(self):
        """
        Disconnects the application from the data logger
        """

        self.start_session_action.setEnabled(False)
        self.stop_session_action.setEnabled(True)
        self.status_bar.showMessage("Starting session")

    def stop_session(self):
        """
        Disconnects the application from the data logger
        """

        self.start_session_action.setEnabled(True)
        self.stop_session_action.setEnabled(False)
        self.status_bar.showMessage("Stopping session")
