import matplotlib
matplotlib.rc_file('matplotlibrc')
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4']='PySide'
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.widgets import Cursor as MplCursor
import PySide.QtGui as Qt
import sys

from blitz.client import BaseApplicationClient
from blitz.ui.mixins import BlitzGuiMixin


class MainBlitzApplication(BaseApplicationClient):

    def __init__(self, args):
        """
        Creates a new desktop application and initialises it
        """
        super(MainBlitzApplication, self).__init__()

        self.gui_application = Qt.QApplication(args)
        self.gui_application.setStyle("plastique")
        self.gui_application.window = MainBlitzWindow(self)
        sys.exit(self.gui_application.exec_())


class BlitzLoggingWidget(Qt.QWidget):
    """
    A widget which handles logger display of data
    """

    def __init__(self, cache, visibility):
        """
        Initialises the graph widget
        """

        super(BlitzLoggingWidget, self).__init__()

        # create widgets
        self.figure = Figure(figsize=(600,600), dpi=72, facecolor=(1,1,1), edgecolor=(1,0,0))

        # create a plot
        self.axis = self.figure.add_subplot(111)
        #FOR CHECKBOXES self.figure.subplots_adjust(left=0.2)

        # add the lines
        self.lines = []
        for series in cache:
            x, y = series
            self.lines += self.axis.plot(x, y, 'o-', linewidth=2)

        # create the canvas
        self.canvas = FigureCanvas(self.figure)

        # initialise the data point label
        self.data_point_label = Qt.QLabel('X: 0.000000, Y: 0.000000')

        # conect up the canvas
        self.canvas.mpl_connect('motion_notify_event', self.mouse_over_event)

        # add checkboxes for selecting visible series
        #FOR CHECKBOXES self.checkbox_labels = ('Item One', 'Item Two')
        #FOR CHECKBOXES also need to draw the checkboxes on a separate axes
        #FOR CHECKBOXES self.series_checkbox = MplCheckButtons(self.axis, self.checkbox_labels, visibility)
        #FOR CHECKBOXES self.series_checkbox.on_clicked(self.toggle_series_visibility)

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

    def toggle_series_visibility(self, label):
        """
        Toggles the visibility of a data series when its checkbox is clicked
        """
        i = self.checkbox_labels.index(label)
        self.lines[i].set_visible(not self.lines[i].get_visible())
        self.canvas.draw()

    def redraw(self, new_data, append=True):
        """
        Redraws the graph when new cached data is supplied

        :param new_data: A list of lists containing new data to be added
        """

        if not append:
            # draw a new plot
            matplotlib.cla()

            self.lines = []
            for series in new_data:
                x, y = series
                self.lines += self.axis.plot(x, y, 'o-')

        else:
            # append data to existing plots
            i = 0
            for line in self.lines:
                line.set_xdata(numpy.append(line.get_xdata(), new_data[i][0]))
                line.set_ydata(numpy.append(line.get_ydata(), new_data[i][1]))
                i += 1

        self.axis.relim()
        self.axis.autoscale_view()
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

        # placeholders for saved data
        self.cache = [
                        ([0,1,2,3], [0.0,1.0,2.0,3.0]),
                        ([0,1,2,3], [0.5,1.5,2.5,3.5]),
                        ([0,1,2,3], [1.0,2.0,3.0,4.0]),
                        ([0,1,2,3], [1.5,2.5,3.5,4.5]),
                        ([0,1,2,3], [2.0,3.0,4.0,5.0]),
                        ([0,1,2,3], [2.5,3.5,4.5,5.5]),
                        ([0,1,2,3], [3.0,4.0,5.0,6.0]),
                        ([0,1,2,3], [3.5,4.5,5.5,6.5]),
                        ([0,1,2,3], [4.0,5.0,6.0,7.0]),
                        ([0,1,2,3], [4.5,5.5,6.5,7.5])
                    ]
        self.cache_visibility = [True]

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
        self.setWindowIcon(Qt.QIcon('static/favicon.ico'))
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

        # exits the application
        self.exit_action = Qt.QAction(Qt.QIcon('blitz/static/img/desktop_exit.png'),'&Exit', self)  # Qt.QIcon('exit.png'), '&Exit', self)
        self.exit_action.setShortcut('Alt+F4')
        self.exit_action.setStatusTip('Exit application')
        self.exit_action.setToolTip('Exit application')
        self.exit_action.triggered.connect(self.close)

        # menus
        self.main_menu = self.menuBar()
        self.file_menu = self.main_menu.addMenu('&File')
        self.logger_menu = self.main_menu.addMenu('&Logger')

        # the toolbar at the top of the window
        self.main_toolbar = self.addToolBar('Main')

        # main graphing widget
        self.main_widget = BlitzLoggingWidget(self.cache, self.cache_visibility)

    def layout_window(self):
        """
        Adds the widgets for the window and generates the layout.

        Automatically called by __init__
        """

        # create the menu bar
        self.file_menu.addAction(self.exit_action)
        self.logger_menu.addAction(self.connect_action)
        self.logger_menu.addAction(self.disconnect_action)
        self.logger_menu.addSeparator()
        self.logger_menu.addAction(self.start_session_action)
        self.logger_menu.addAction(self.stop_session_action)

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

    def update_cached_data(self, data, append=True):
        """
        Updates the cached and plotted data, optionally clearing the existing data

        :param data: The x-y data that should be appended to cached data
        :param append: If false, the existing data will be entirely replaced as opposed ot appended.  Default True

        :returns: Nothing
        """
        pass

