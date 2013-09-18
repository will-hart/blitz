import sys
import PySide.QtGui as Qt
from blitz.ui.mixins import BlitzGuiMixin

class MainBlitzApplication(Qt.QApplication):

    def __init__(self, args):
        """
        Creates a new desktop application and initialises it
        """
        super(MainBlitzApplication, self).__init__(args)

        self.window = MainBlitzWindow(self)
        sys.exit(self.exec_())


class BlitzLoggingWidget(Qt.QWidget):
    """
    A widget which handles logger display of data
    """

    def __init__(self):
        """
        Initialises the graph widget
        """

        super(BlitzLoggingWidget, self).__init__()

        # create widgets
        self.button1 = Qt.QPushButton('button1', self)
        self.grid = Qt.QGridLayout()

        # layout widgets
        self.grid.setSpacing(10)
        self.grid.addWidget(self.button1, 0, 0)
        self.grid.addWidget(Qt.QLabel(''), 0, 1, 1, 3)

        # Save the layout
        self.setLayout(self.grid)


class MainBlitzWindow(Qt.QMainWindow, BlitzGuiMixin):
    """
    Contains a Qt Main Window that handles user interactions on the Blitz Logger desktop software
    """
    def __init__(self, app):
        """
        Initialises the main window
        """
        super(MainBlitzWindow, self).__init__()

        self.app = app

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
        self.connect_action = Qt.QAction('&Connect', self)
        self.connect_action.setShortcut('Ctrl+C')
        self.connect_action.setStatusTip("Connects to the data logger over the network")
        self.connect_action.triggered.connect(self.connect_to_logger)

        # disconnects from the logger
        self.disconnect_action = Qt.QAction('&Disconnect', self)
        self.disconnect_action.setShortcut('Ctrl+Shift+C')
        self.disconnect_action.setStatusTip("Disconnect from the data logger")
        self.disconnect_action.triggered.connect(self.disconnect_from_logger)
        self.disconnect_action.setEnabled(False)

        # starts a logging session
        self.start_session_action = Qt.QAction('&Start', self)
        self.start_session_action.setShortcut('F5')
        self.start_session_action.setStatusTip("Starts a logging session")
        self.start_session_action.triggered.connect(self.start_session)
        self.start_session_action.setEnabled(False)

        # stops a logging session
        self.stop_session_action = Qt.QAction('S&top', self)
        self.stop_session_action.setShortcut('Shift+F5')
        self.stop_session_action.setStatusTip("Stops a logging session")
        self.stop_session_action.triggered.connect(self.stop_session)
        self.stop_session_action.setEnabled(False)

        # exits the application
        self.exit_action = Qt.QAction('&Exit', self)  # Qt.QIcon('exit.png'), '&Exit', self)
        self.exit_action.setShortcut('Alt+F4')
        self.exit_action.setStatusTip('Exit application')
        self.exit_action.triggered.connect(self.close)

        # menus
        self.main_menu = self.menuBar()
        self.file_menu = self.main_menu.addMenu('&File')
        self.logger_menu = self.main_menu.addMenu('&Logger')

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
