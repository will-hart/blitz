from datetime import datetime
import matplotlib

from blitz.data import DataContainer
from blitz.data.models import Session

matplotlib.rc_file('matplotlibrc')
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4']='PySide'
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor as MplCursor
import PySide.QtGui as Qt
import PySide.QtCore as QtCore
import sys

from blitz.client import BaseApplicationClient
import blitz.communications.signals as sigs
from blitz.ui.mixins import BlitzGuiMixin
from blitz.utilities import blitz_strftimestamp


class MainBlitzApplication(BaseApplicationClient):

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

    def __init__(self):
        """
        Initialises the graph widget
        """

        super(BlitzLoggingWidget, self).__init__()

        # set up the required data structures
        self.__lines = {}
        self.__container = DataContainer()

        # create widgets
        self.figure = Figure(figsize=(1024, 768), dpi=72, facecolor=(1, 1, 1), edgecolor=(1, 0, 0))

        # create a plot
        self.axis = self.figure.add_subplot(111)
        #self.figure.subplots_adjust(left=0.2)

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
            self.__container = DataContainer()

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
                self.__lines[key], = self.axis.plot([], [], 'o-')

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
            self.axis.set_ylim(bottom=self.__container.y_min * 0.9 - 1, top=self.__container.y_max * 1.1 + 1, auto=False)

        # redraw if required
        if draw_canvas:
            self.canvas.draw()


class MainBlitzWindow(Qt.QMainWindow, BlitzGuiMixin):
    """
    Contains a Qt Main Window that handles user interactions on the Blitz Logger desktop software
    """
    def __init__(self, app):
        """
        Initialises the main window
        """
        super(MainBlitzWindow, self).__init__()

        self.application = app

        self.initialise_window()

        self.generate_widgets()

        self.layout_window()

        self.run_window()

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
        # status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Blitz Logger is ready")

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

        # view a session list
        self.session_list_action = Qt.QAction('View Session List', self)
        #self.session_list_action.setEnabled(False)
        self.session_list_action.setStatusTip("View previously logged sessions")
        self.session_list_action.setToolTip("View previously logged sessions")
        self.session_list_action.setShortcut('Ctrl+L')
        self.session_list_action.triggered.connect(self.show_session_list)

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

        # menus
        self.main_menu = self.menuBar()
        self.file_menu = self.main_menu.addMenu('&File')
        self.logger_menu = self.main_menu.addMenu('&Logger')
        self.session_menu = self.main_menu.addMenu('&Session')

        # the toolbar at the top of the window
        self.main_toolbar = self.addToolBar('Main')

        # main graphing widget
        self.main_widget = BlitzLoggingWidget()

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

        self.session_menu.addAction(self.session_list_action)

        # create the toolbar
        self.main_toolbar.addAction(self.connect_action)
        self.main_toolbar.addAction(self.disconnect_action)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction(self.start_session_action)
        self.main_toolbar.addAction(self.stop_session_action)

        # set the central widget
        self.setCentralWidget(self.main_widget)

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
        :param replace_existing: If false, the existing data will be entirely replaced as opposed ot appended.  Default True

        :returns: Nothing
        """

        #for k in data.keys():
        #    # convert from Python datetime to matplotlib datenum
        #    data[k][0] = [MplDates.date2num(x) for x in data[k][0]]

        self.main_widget.redraw(data, replace_existing)

    def show_session_list(self):
        # first get the list of sessions
        raw_sessions = self.application.data.all(Session)
        sessions = []

        for sess in raw_sessions:
            dt = blitz_strftimestamp(sess.timeStarted)

            sessions.append([
                "Session %s (%s readings) started %s" % (sess.ref_id, sess.numberOfReadings, dt),
                sess.available,
                sess.ref_id
            ])

        self.session_list_window = BlitzSessionWindow(self.application, sessions)
        self.session_list_window.show()


class BlitzSessionWindow(Qt.QWidget):
    """
    A UI window which lists available data logger sessions and
    """

    def __init__(self, application, session_list=None):

        super(BlitzSessionWindow, self).__init__()

        self.application = application

        self.setWindowTitle("Session List")
        self.resize(800, 600)

        self.selected_item_id = -1

        self.session_table = Qt.QListView(self)
        self.model = Qt.QStandardItemModel(self.session_table)

        for row in session_list:
            item = Qt.QStandardItem(row[0])
            item.setCheckable(True)
            item.setCheckState(QtCore.Qt.Checked if row[1] else QtCore.Qt.Unchecked)
            item.sessionId = row[2]
            self.model.appendRow(item)

        self.model.itemChanged.connect(self.on_item_checked)

        self.session_table.setModel(self.model)

        self.download_button = Qt.QPushButton("Download")
        self.download_button.clicked.connect(self.download_session)

        self.view_series_button = Qt.QPushButton("View Graphs")

        self.grid = Qt.QGridLayout()
        self.grid.addWidget(self.session_table, 0, 0, 4, 5)
        self.grid.addWidget(self.download_button, 0, 5)
        self.grid.addWidget(self.view_series_button, 1, 5)
        self.setLayout(self.grid)

    def on_item_checked(self, item):
        """
        Handles clicking a checkbox in the session list.  Unchecked sessions
        are deleted from the database whilst checked sessions are downloaded

        :param item: The item that was checked/unchecked
        """

        if item.checkState():
            # download
            sigs.client_requested_download.send(item.sessionId)

        else:
            # delete local session data?
            # TODO implement...
            pass

    def download_session(self):
        """
        Handles the 'download session' button being clicked on a session list item
        """

        # get the session ID of the selected item
        selected_item = self.session_table.selectedIndexes()
        if len(selected_item) <= 0:
            return
        else:
            selected_item = selected_item[0]

        current_item = selected_item.model().item(selected_item.row())
        current_idx = current_item.sessionId

        # check we have the item downloaded and trigger download if we do not
        if not current_item.checkState():
            self.on_item_checked(current_item)

        # get the data
        data = self.application.data.get_session_readings(current_idx)
        raw_sess_vars = self.application.data.get_session_variables(current_idx)
        sess_vars = dict([(x.id, x.variableName) for x in raw_sess_vars])

        # prepare the string to write to file
        output = "Time Logged,Variable Name,Value\r\n"
        for row in data:
            output += "%s,%s,%s\n" % (
                blitz_strftimestamp(max(0, row.timeLogged)),
                sess_vars[row.categoryId],
                row.value
            )

        # get the file name
        file_path, _ = Qt.QFileDialog.getSaveFileName(self, 'Save session to file...', 'C:/', 'CSV Files (*.csv)')

        # write to file
        with open(file_path, 'w') as f:
            f.write(output)