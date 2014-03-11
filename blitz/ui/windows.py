from datetime import datetime
import matplotlib

from blitz.data import DataContainer
from blitz.data.models import Session

matplotlib.rc_file('matplotlibrc')
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4'] = 'PySide'
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor as MplCursor
import PySide.QtGui as Qt
import PySide.QtCore as QtCore
import sys

from blitz.client import ApplicationClient
import blitz.communications.signals as sigs
from blitz.communications.rs232 import ExpansionBoardNotFound
from blitz.ui.mixins import BlitzGuiMixin
from blitz.ui.processing_dialog import ProcessingDialog
from blitz.ui.calibration_dialog import CalibrationDialog
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
    boards_updated =  QtCore.Signal(dict)

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


class BlitzLoggingWidget(Qt.QWidget):
    """
    A widget which handles logger display of data
    """

    def __init__(self, container):
        """
        Initialises the graph widget
        """

        super(BlitzLoggingWidget, self).__init__()

        # set up the required data structures
        self.__lines = {}
        self.__container = container

        # create widgets
        self.figure = Figure(figsize=(800, 600), dpi=72, facecolor=(1, 1, 1), edgecolor=(1, 0, 0))

        # create a plot
        self.axis = self.figure.add_subplot(111)

        # build the chart but do not draw it yet - wait until the application is drawn
        self.redraw({}, True, False)

        # create the canvas
        self.canvas = FigureCanvas(self.figure)

        # initialise the data point label
        self.data_point_label = Qt.QLabel('X: 0.000000, Y: 0.000000')

        # conect up the canvas
        self.canvas.mpl_connect('motion_notify_event', self.mouse_over_event)

        # create a cursor
        self.data_cursor = MplCursor(self.axis, useblit=True, color='blue', linewidth=1)

        # layout widgets
        self.grid = Qt.QGridLayout()
        self.grid.addWidget(self.canvas, 0, 0, 1, 3)
        self.grid.addWidget(self.data_point_label, 1, 0)

        # Save the layout
        self.setLayout(self.grid)

    def mouse_over_event(self, event):
        """
        Handles the mouse rolling over the plot
        """

        if not event.inaxes:
            self.data_point_label.setText('X: 0.000000, Y: 0.000000')
        else:
            self.data_point_label.setText(self.axis.format_coord(event.xdata, event.ydata))

    def redraw(self, new_data, replace_existing=False, draw_canvas=True):
        """
        Redraws the graph when new cached data is supplied

        :param new_data: A list of lists containing new data to be added
        :param replace_existing: If True, then the existing data will be deleted before appending
        :param draw_canvas: Prevents attempting to draw the canvas before the Qt window is drawn on startup
        """
        if replace_existing:
            # clear the existing plot
            self.axis.cla()
            self.__lines = {}
            self.__container.clear_data()

            self.axis.set_xlabel("Time Logged (s)")
            self.axis.set_ylabel("Value")

        for key in new_data.keys():
            # massage key to str
            key = str(key)

            # get the new plot data
            x, y = new_data[key]

            # push the new plot data on to the Container, checking if we need a new plot
            if self.__container.push(key, x, y):
                # TODO: determine how to manage plot ordering and new variables being suddenly added
                # TODO: after a 'replace_existing'
                # add an empty plot and record the ID
                self.__lines[key], = self.axis.plot([], [], 'o-', label=key)

            x, y = self.__container.get_series(key)

            # update the chart at the correct index
            self.__lines[key].set_xdata(x)
            self.__lines[key].set_ydata(y)

        # tidy up and rescale
        if self.__container.empty():
            self.axis.set_xlim(left=0, right=100)
            self.axis.set_ylim(bottom=0, top=100)
        else:
            self.axis.set_xlim(left=self.__container.x_min - 1, right=self.__container.x_max + 1, auto=False)
            self.axis.set_ylim(
                bottom=self.__container.y_min * 0.9 - 1, top=self.__container.y_max * 1.1 + 1, auto=False)

        # redraw if required
        if draw_canvas:
            self.axis.legend(loc='upper left')
            self.canvas.draw()

    def clear_graphs(self):
        """
        Clears the graphs in the logging display
        """
        self.__container.clear_data()
        self.redraw({}, True)


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
            self, "Blitz Data Logger Error", "There has been an error communicating with the logger!" + \
            " The error code is: \n\n\t\t{0}\n\nYou can try resetting the data logger using ".format(error) + \
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
        self.variable_widget.set_data(self.__container.get_latest())

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

    def get_session_list(self):
        sigs.client_requested_session_list.send()

    def update_connected_boards(self, data):
        self.board_list_widget.set_data(data)
        sigs.process_finished.send()

    def calibrate(self):
        """
        Shows the calibration form
        """

        self.__calibration_win = CalibrationDialog(5, 0, 40, "deg", "09")
        self.__calibration_win.show()

    def reset_device(self):
        sigs.force_board_reset.send()

    def send_boards_request(self):
        """
        Sends a request for connected expansion boards to the server
        """
        sigs.process_started.send("Requesting connected boards")
        sigs.board_list_requested.send()


class BlitzTableView(Qt.QWidget):
    """
    A UI tab pane which shows teh last variable read from each channel in the current session data
    """
    def __init__(self, headers, stretch_columns=True):

        super(BlitzTableView, self).__init__()

        self.__cols = len(headers)
        self.__headers = headers
        self.__stretch = stretch_columns

        # set up the table
        self.variable_table = Qt.QTableWidget()
        self.variable_table.setColumnCount(self.__cols)
        self.variable_table.setHorizontalHeaderLabels(self.__headers)
        self.variable_table.setSelectionBehavior(Qt.QAbstractItemView.SelectRows)
        self.variable_table.setSelectionMode(Qt.QAbstractItemView.SingleSelection)
        self.variable_table.setEditTriggers(Qt.QAbstractItemView.NoEditTriggers)

        # slots/signals
        self.variable_table.itemSelectionChanged.connect(self.selection_changed)

        if self.__stretch:
            self.variable_table.horizontalHeader().setResizeMode(Qt.QHeaderView.Stretch)
        else:
            self.variable_table.horizontalHeader().setResizeMode(Qt.QHeaderView.ResizeToContents)

    def selection_changed(self):
        pass

    def build_layout(self):
        self.grid = Qt.QGridLayout()
        self.grid.addWidget(self.variable_table, 0, 0)
        self.setLayout(self.grid)

    def set_data(self, data):
        """
        Sets the data on the table by providing a 2d list of variable/value pairs

        :param data: the list of variable/value pairs
        """

        self.variable_table.clear()
        self.variable_table.setRowCount(len(data))

        for i, row in enumerate(data):
            for j, val in enumerate(row):
                self.variable_table.setItem(i, j, Qt.QTableWidgetItem("{0}".format(val)))

        self.variable_table.setHorizontalHeaderLabels(self.__headers)


class BlitzSessionTabPane(BlitzTableView):
    """
    A UI tab pane which lists available data logger sessions and
    """

    def __init__(self, headers, application):

        super(BlitzSessionTabPane, self).__init__(headers, False)

        self.application = application
        self.__selected_id = -1
        self.__connected = False

        # button for downloading sessions
        self.download_button = Qt.QPushButton(Qt.QIcon('blitz/static/img/desktop_download.png'),"Download", self)
        self.download_button.setFlat(True)
        self.download_button.clicked.connect(self.download_session)
        self.download_button.setEnabled(False)

        # button for saving sessions
        self.save_button = Qt.QPushButton(Qt.QIcon('blitz/static/img/desktop_save.png'),"Export", self)
        self.save_button.setFlat(True)
        self.save_button.clicked.connect(self.save_session)
        self.save_button.setEnabled(False)

        # button for viewing session plots
        self.view_series_button = Qt.QPushButton(Qt.QIcon('blitz/static/img/desktop_graph_large.png'),"View", self)
        self.view_series_button.setFlat(True)
        self.view_series_button.setEnabled(False)

        # button for deleting sessions
        self.delete_session_button = Qt.QPushButton(Qt.QIcon('blitz/static/img/desktop_delete.png'),"Delete", self)
        self.delete_session_button.setFlat(True)
        self.delete_session_button.setEnabled(False)

    def set_connected(self, connected):
        """
        Sets a flag indicating whether the logger is currently connected
        """
        self.__connected = connected

    def build_layout(self):
        # revised grid
        self.grid = Qt.QGridLayout()
        self.grid.addWidget(self.variable_table, 0, 0, 5, 5)
        self.grid.addWidget(self.download_button, 0, 5)
        self.grid.addWidget(self.save_button, 1, 5)
        self.grid.addWidget(self.view_series_button, 2, 5)
        self.grid.addWidget(self.delete_session_button, 3, 5)
        self.setLayout(self.grid)

    def selection_changed(self):
        items = self.variable_table.selectedItems()
        self.__selected_id = int(items[1].text()) if items else -1

        # update GUI
        self.save_button.setEnabled(self.__selected_id >= 0 and (items[0].text() == "X" or self.__connected))
        self.download_button.setEnabled(self.__selected_id >= 0 and self.__connected)
        # self.view_series_button.setEnabled(self.__selected_id >= 0)
        # self.delete_session_button.setEnabled(self.__selected_id >= 0)

    def download_session(self):
        if self.__selected_id < 0:
            return
        self.trigger_session_download(self.__selected_id)

    @staticmethod
    def trigger_session_download(session_id):
        """
        Handles clicking a checkbox in the session list.  Unchecked sessions
        are deleted from the database whilst checked sessions are downloaded

        :param session_id: The session ref_id to download
        """
        sigs.process_started.send("Downloading data")
        sigs.client_requested_download.send(session_id)

    def save_session(self):
        """
        Handles the 'download session' button being clicked on a session list item
        """

        # get the session ID of the selected item
        selected_items = self.variable_table.selectedItems()

        if len(selected_items) <= 0:
            return

        selected_idx = int(selected_items[1].text())
        available = selected_items[0].text() == "X"

        # get the file name
        file_path, _ = Qt.QFileDialog.getSaveFileName(self, 'Save session to file...', 'C:/', 'CSV Files (*.csv)')

        # check we have the item downloaded and trigger download if we do not
        if not available:
            self.trigger_session_download(selected_idx)

        # show the saving dialogue
        sigs.process_started.send("Saving data")

        # get the data
        data = self.application.data.get_session_readings(selected_idx)
        sess = self.application.data.get(Session, {"id": selected_idx})
        raw_sess_vars = self.application.data.get_session_variables(selected_idx)
        sess_vars = dict([(x.id, x.variableName) for x in raw_sess_vars])

        # prepare the string to write to file
        output = "Time Logged,Elapsed Seconds, Variable Name,Value\n"
        for row in data:
            output += "%s,%s,%s,%s\n" % (
                blitz_strftimestamp(sess.timeStarted + row.timeLogged),
                row.timeLogged / 1000.0,
                sess_vars[row.categoryId],
                row.value
            )

        # write to file if a path was given
        if file_path:
            with open(file_path, 'w') as f:
                f.write(output)

        sigs.process_finished.send()
