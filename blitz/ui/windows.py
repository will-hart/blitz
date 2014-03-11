from blitz.data import DataContainer
from blitz.data.models import Session

import PySide.QtGui as Qt
import PySide.QtCore as QtCore
import sys

from blitz.client import ApplicationClient
import blitz.communications.signals as sigs
from blitz.communications.rs232 import ExpansionBoardNotFound
from blitz.ui.mixins import BlitzGuiMixin
from blitz.ui.dialogs import ProcessingDialog, CalibrationDialog
from blitz.ui.widgets import BlitzLoggingWidget, BlitzTableView, BlitzSessionTabPane
from blitz.utilities import blitz_strftimestamp


class GUISignalEmitter(QtCore.QObject):
    """
    Used for passing events and signals from other threads onto the GUI thread
    """
    tcp_lost = QtCore.Signal()
    task_started = QtCore.Signal(str)
    task_finished = QtCore.Signal()
    board_error = QtCore.Signal(str)
    logging_started = QtCore.Signal()
    logging_stopped = QtCore.Signal()
    boards_updated = QtCore.Signal(dict)

    def __init__(self):
        super(GUISignalEmitter, self).__init__()
        sigs.lost_tcp_connection.connect(self.trigger_connection_lost)
        sigs.process_started.connect(self.trigger_task_started)
        sigs.process_finished.connect(self.trigger_task_finished)
        sigs.logger_error_received.connect(self.trigger_board_error)
        sigs.logging_started.connect(self.trigger_logging_started)
        sigs.logging_stopped.connect(self.trigger_logging_stopped)
        sigs.board_list_processed.connect(self.trigger_boards_updated)

    def trigger_connection_lost(self, args):
        self.tcp_lost.emit()

    def trigger_task_started(self, description):
        self.task_started.emit(description)

    def trigger_task_finished(self, args):
        self.task_finished.emit()

    def trigger_board_error(self, args):
        self.board_error.emit(args)

    def trigger_logging_started(self, args):
        self.logging_started.emit()

    def trigger_logging_stopped(self, args):
        self.logging_stopped.emit()

    def trigger_boards_updated(self, boards):
        self.boards_updated.emit(boards)


class MainBlitzApplication(ApplicationClient):

    def __init__(self, args):
        """
        Creates a new desktop application and initialises it
        """
        super(MainBlitzApplication, self).__init__()

        self.gui_application = Qt.QApplication(args)
        self.gui_application.setStyle("plastique")
        self.gui_application.window = MainBlitzWindow(self)
        self.gui_application.setWindowIcon(Qt.QIcon('blitz/static/img/blitz.png'))
        sys.exit(self.gui_application.exec_())

    def update_interface(self, data, replace_existing=False):
        """
        Provides an implementation of BaseApplicationClient.update_interface.

        :param data: The results received from the BoardManager.parse_message command
        :param replace_existing: If True, appends to existing cache, if False, replaces cache? Defaults to False

        :returns: Nothing
        """

        result = super(MainBlitzApplication, self).update_interface(data, replace_existing)

        if result:
            self.gui_application.window.update_cached_data(result, replace_existing)


class MainBlitzWindow(Qt.QMainWindow, BlitzGuiMixin):
    """
    Contains a Qt Main Window that handles user interactions on the Blitz Logger desktop software
    """
    def __init__(self, app):
        """
        Initialises the main window
        """
        super(MainBlitzWindow, self).__init__()

        # connect up external signals
        self.__signaller = GUISignalEmitter()
        self.__signaller.tcp_lost.connect(self.connection_lost)
        self.__signaller.task_started.connect(self.show_process_dialogue)
        self.__signaller.task_finished.connect(self.update_session_list)
        self.__signaller.board_error.connect(self.show_board_error)
        self.__signaller.logging_started.connect(self.logging_started_ui_update)
        self.__signaller.logging_stopped.connect(self.logging_stopped_ui_update)
        self.__signaller.boards_updated.connect(self.update_connected_boards)

        # create a data context for managing data
        self.__container = DataContainer()

        self.application = app

        self.initialise_window()

        self.generate_widgets()

        self.layout_window()

        self.run_window()

        # create a handle for a processing dialogue
        self.__indicator = None
        self.__calibration_win = None

    def show_process_dialogue(self, description):
        self.__indicator = ProcessingDialog(self.__signaller.task_finished, description)
        self.__indicator.show()

    def show_board_error(self, error):
        """
        Displays a board error to the user and suggests a logger reset
        """
        # inform the user
        Qt.QMessageBox.critical(
            self, "Blitz Data Logger Error", "There has been an error communicating with the logger!" +
            " The error code is: \n\n\t\t{0}\n\nYou can try resetting the data logger using ".format(error) +
            "the 'logger' menu - this may result in the loss of logged data.")
        self.status_bar.showMessage("The connection to the data logger has been lost")

    def connection_lost(self):
        """
        Triggered when the connection is lost - tidies up the UI
        """

        # disconnect TCP and update the UI
        self.application.tcp = None
        self.disconnect_from_logger(ui_only=True)

        # inform the user
        Qt.QMessageBox.critical(
            self, "Blitz Data Logger Connection Error", "Unable to establish a connection to the data logger")
        self.status_bar.showMessage("The connection to the data logger has been lost")
        sigs.process_finished.send()

    def initialise_window(self):
        """
        Sets up the window parameters such as icon, title

        Automatically called by __init__
        """
        # icons
        self.setWindowIcon(Qt.QIcon('blitz/static/img/blitz.png'))
        self.setWindowTitle("Blitz Data Logger")

        # size
        self.resize(1024, 768)

        # fonts
        Qt.QToolTip.setFont(Qt.QFont('SansSerif', 10))

    def generate_widgets(self):
        """
        Creates the widgets that are displayed on the window

        Automatically created by __init__
        """

        ##
        # menu bar actions
        ##

        # connects to the logger
        self.connect_action = Qt.QAction(Qt.QIcon('blitz/static/img/desktop_connect.png'), '&Connect', self)
        self.connect_action.setShortcut('Ctrl+C')
        self.connect_action.setStatusTip("Connects to the data logger over the network")
        self.connect_action.setToolTip("Connects to the data logger over the network")
        self.connect_action.triggered.connect(self.connect_to_logger)

        # disconnects from the logger
        self.disconnect_action = Qt.QAction(Qt.QIcon('blitz/static/img/desktop_disconnect.png'), '&Disconnect', self)
        self.disconnect_action.setShortcut('Ctrl+Shift+C')
        self.disconnect_action.setStatusTip("Disconnect from the data logger")
        self.disconnect_action.setToolTip("Disconnect from the data logger")
        self.disconnect_action.triggered.connect(self.disconnect_from_logger)
        self.disconnect_action.setEnabled(False)

        # starts a logging session
        self.start_session_action = Qt.QAction(Qt.QIcon('blitz/static/img/desktop_start.png'), '&Start', self)
        self.start_session_action.setShortcut('F5')
        self.start_session_action.setStatusTip("Starts a logging session")
        self.start_session_action.setToolTip("Starts a logging session")
        self.start_session_action.triggered.connect(self.start_session)
        self.start_session_action.setEnabled(False)

        # stops a logging session
        self.stop_session_action = Qt.QAction(Qt.QIcon('blitz/static/img/desktop_stop.png'), 'S&top', self)
        self.stop_session_action.setShortcut('Shift+F5')
        self.stop_session_action.setStatusTip("Stops a logging session")
        self.stop_session_action.setToolTip("Stops a logging session")
        self.stop_session_action.triggered.connect(self.stop_session)
        self.stop_session_action.setEnabled(False)

        # calibrate logger
        self.calibration_action = Qt.QAction('&Calibrate', self)
        self.calibration_action.setStatusTip("Calibrates exansion board")
        self.calibration_action.setToolTip("Calibrates the expansion board")
        self.calibration_action.triggered.connect(self.calibrate)
        self.calibration_action.setEnabled(False)

        # force reset device
        self.reset_device_action = Qt.QAction(Qt.QIcon('blitz/static/img/desktop_reset.png'), '&Reset', self)
        self.reset_device_action.setStatusTip("Reset logger to idle state")
        self.reset_device_action.setToolTip("Forces the logger to reset to idle state")
        self.reset_device_action.triggered.connect(self.reset_device)
        self.reset_device_action.setEnabled(False)

        # send a session list request
        self.update_session_listing_action = Qt.QAction(
            Qt.QIcon('blitz/static/img/desktop_session_list.png'), '&Update session list', self)
        self.update_session_listing_action.setStatusTip("Get a list of logging sessions from the data logger")
        self.update_session_listing_action.setToolTip("Get logger session list")
        self.update_session_listing_action.triggered.connect(self.get_session_list)
        self.update_session_listing_action.setEnabled(False)

        # send a board list request
        self.update_board_listing_action = Qt.QAction(
            Qt.QIcon('blitz/static/img/desktop_session_list.png'), 'Update &board list', self)
        self.update_board_listing_action.setStatusTip("Get a list of expansion boards connected to the data logger")
        self.update_board_listing_action.setToolTip("Get logger board list")
        self.update_board_listing_action.triggered.connect(self.send_boards_request)
        self.update_board_listing_action.setEnabled(False)

        # shows the settings window
        self.settings_action = Qt.QAction('&Settings', self)
        self.settings_action.setShortcut('Ctrl+Alt+S')
        self.settings_action.setStatusTip('Manage application settings')
        self.settings_action.setToolTip('Manage application settings')
        #self.exit_action.triggered.connect(self.close)
        self.settings_action.setEnabled(False)

        # exits the application
        self.exit_action = Qt.QAction(Qt.QIcon('blitz/static/img/desktop_exit.png'), '&Exit', self)
        self.exit_action.setShortcut('Alt+F4')
        self.exit_action.setStatusTip('Exit application')
        self.exit_action.setToolTip('Exit application')
        self.exit_action.triggered.connect(self.close)

        # label for diffuser position
        self.motor_control_label = Qt.QLabel(" Diffuser position: ")

        # allows setting of the motor angle
        self.motor_control = Qt.QSpinBox()
        self.motor_control.setMinimum(0)
        self.motor_control.setMaximum(40)
        self.motor_control.setValue(0)
        self.motor_control.setEnabled(False)
        self.motor_control.valueChanged.connect(self.set_motor_position)

        # menus
        self.main_menu = self.menuBar()
        self.file_menu = self.main_menu.addMenu('&File')
        self.logger_menu = self.main_menu.addMenu('&Logger')

        # the toolbar at the top of the window
        self.main_toolbar = self.addToolBar('Main')

        # widgets to show in the tab
        self.plot_widget = BlitzLoggingWidget(self.__container)
        self.variable_widget = BlitzTableView(["Variable", "Value"])
        self.variable_widget.build_layout()
        self.session_list_widget = BlitzSessionTabPane(["", "ID", "Readings", "Date"], self.application)
        self.session_list_widget.build_layout()
        self.board_list_widget = BlitzTableView(["ID", "Description"])
        self.board_list_widget.build_layout()
        self.update_session_list()

        # tabbed widget for session and variable
        self.__tab_widget = Qt.QTabWidget()
        self.__tab_widget.setMinimumWidth(300)
        self.__tab_widget.addTab(self.variable_widget, "Variables")
        self.__tab_widget.addTab(self.session_list_widget, "Sessions")
        self.__tab_widget.addTab(self.board_list_widget, "Boards")

        # create a layout grid
        self.__layout = Qt.QSplitter()
        self.__layout.addWidget(self.plot_widget)
        self.__layout.addWidget(self.__tab_widget)

    def layout_window(self):
        """
        Adds the widgets for the window and generates the layout.

        Automatically called by __init__
        """

        # create the menu bar
        self.file_menu.addAction(self.settings_action)
        self.logger_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.logger_menu.addAction(self.connect_action)
        self.logger_menu.addAction(self.disconnect_action)
        self.logger_menu.addSeparator()
        self.logger_menu.addAction(self.start_session_action)
        self.logger_menu.addAction(self.stop_session_action)
        self.logger_menu.addSeparator()
        self.logger_menu.addAction(self.calibration_action)
        self.logger_menu.addAction(self.reset_device_action)
        self.logger_menu.addAction(self.update_session_listing_action)
        self.logger_menu.addAction(self.update_board_listing_action)

        # create the toolbar
        self.main_toolbar.addAction(self.connect_action)
        self.main_toolbar.addAction(self.disconnect_action)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction(self.start_session_action)
        self.main_toolbar.addAction(self.stop_session_action)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addWidget(self.motor_control_label)
        self.main_toolbar.addWidget(self.motor_control)

        # create a grid to display the main widgets
        self.setCentralWidget(self.__layout)

        # status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Blitz Logger is ready")

    def run_window(self):
        """
        Connects the required signals and displays the window

        Automatically called by __init__
        """
        # go go go
        self.show()

    def update_cached_data(self, data, replace_existing=True):
        """
        Updates the cached and plotted data, optionally clearing the existing data

        :param data: The x-y data that should be appended to cached data
        :param replace_existing: If false, the existing data will be entirely replaced as opposed to appended.

        :returns: Nothing
        """

        #for k in data.keys():
        #    # convert from Python datetime to matplotlib datenum
        #    data[k][0] = [MplDates.date2num(x) for x in data[k][0]]

        self.plot_widget.redraw(data, replace_existing)

        # update the variable view from the container
        self.variable_widget.set_data(self.__container.get_latest(named=True))

    def update_session_list(self):
        # first get the list of sessions
        raw_sessions = self.application.data.all(Session)
        sessions = []

        for sess in raw_sessions:
            dt = blitz_strftimestamp(sess.timeStarted)

            sessions.append([
                "X" if sess.available else "",
                sess.ref_id,
                sess.numberOfReadings,
                dt
            ])

        self.session_list_widget.set_data(sessions)

    def set_motor_position(self):
        """
        Sets the motor position from the QSpinBox in the toolbar
        """
        pos = self.motor_control.value()
        try:
            self.send_move_command(pos)
        except ExpansionBoardNotFound:
            self.status_bar.showMessage("ERROR! Unable to contact the expansion board to set motor position")
        else:
            self.status_bar.showMessage("Set motor to %s" % pos)

    def update_connected_boards(self, data):
        self.board_list_widget.set_data(data)
        sigs.process_finished.send()

    def calibrate(self):
        """
        Shows the calibration form
        """

        self.__calibration_win = CalibrationDialog(5, 0, 40, "deg", "09")
        self.__calibration_win.show()

    @staticmethod
    def reset_device():
        sigs.force_board_reset.send()

    @staticmethod
    def send_boards_request():
        """
        Sends a request for connected expansion boards to the server
        """
        sigs.process_started.send("Requesting connected boards")
        sigs.board_list_requested.send()

    @staticmethod
    def get_session_list():
        sigs.client_requested_session_list.send()
