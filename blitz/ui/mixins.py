class BlitzGuiMixin(object):
    def connect_to_logger(self, ui_only=False):
        """
        Connects the application to the data logger via a TCP connection

        :param ui_only: Defaults to False which will update the application and UI, set to True to only affect the UI
        """

        if not ui_only:
            self.application.connect_to_logger()

        # update the UI
        self.connect_action.setEnabled(False)
        self.disconnect_action.setEnabled(True)
        self.start_session_action.setEnabled(True)
        self.stop_session_action.setEnabled(False)
        self.update_session_listing_action.setEnabled(True)
        self.calibration_action.setEnabled(True)
        self.motor_control.setEnabled(True)
        self.reset_device_action.setEnabled(True)
        self.status_bar.showMessage("Connected to logger")
        self.session_list_widget.set_connected(True)

    def disconnect_from_logger(self, ui_only=False):
        """
        Disconnects the application from the data logger

        :param ui_only: Defaults to False which will update the application and UI, set to True to only affect the UI
        """

        if not ui_only:
            self.application.connect_to_logger()

        # update the UI
        self.connect_action.setEnabled(True)
        self.disconnect_action.setEnabled(False)
        self.start_session_action.setEnabled(False)
        self.stop_session_action.setEnabled(False)
        self.update_session_listing_action.setEnabled(False)
        self.calibration_action.setEnabled(False)
        self.motor_control.setEnabled(False)
        self.reset_device_action.setEnabled(False)
        self.status_bar.showMessage("Disconnected from logger")
        self.session_list_widget.set_connected(False)

    def start_session(self):
        """
        Disconnects the application from the data logger
        """

        self.application.start_logging()

    def logging_started_ui_update(self):
        """
        Updates the UI when logging has started
        """
        self.start_session_action.setEnabled(False)
        self.stop_session_action.setEnabled(True)
        self.update_session_listing_action.setEnabled(False)
        self.calibration_action.setEnabled(False)
        self.status_bar.showMessage("Starting session")

        # clear the container on the logging widget
        self.plot_widget.clear_graphs()

    def stop_session(self):
        """
        Disconnects the application from the data logger
        """
        self.application.stop_logging()

    def logging_stopped_ui_update(self):
        """
        Updates the UI when logging has stopped
        """
        self.start_session_action.setEnabled(True)
        self.stop_session_action.setEnabled(False)
        self.update_session_listing_action.setEnabled(True)
        self.calibration_action.setEnabled(True)
        self.status_bar.showMessage("Stopping session")

    def send_move_command(self, angle):
        # clamp to safe range
        if angle < 0:
            angle = 0
        if angle > 40:
            angle = 40

        # start the command - 0985 is the "set motor on board 09" command
        # the following 8 zeroes are the timestamp
        command = '09850000000000'

        # build the message - the angle should be packed as a sixteen bit hex value
        command += hex(angle).replace('0x', '').rjust(2, '0')

        # send the command
        self.application.send_command(command)
