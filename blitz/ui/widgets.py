from datetime import datetime
import matplotlib

matplotlib.rc_file('matplotlibrc')
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4'] = 'PySide'

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor as MplCursor
from PySide import QtGui as Qt

import blitz.communications.signals as sigs


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
            self.__container.clear_data()

        self.axis.cla()
        self.__lines = {}
        self.axis.set_xlabel("Time Logged (s)")
        self.axis.set_ylabel("Value")

        for key in new_data.keys():
            series_id, series_name = key

            # get the new plot data
            x, y = new_data[key]
            self.__container.push(series_id, series_name, x, y)

            x, y = self.__container.get_series(series_id)
            self.__lines[series_id], = self.axis.plot(x, y, 'o-', label=series_name.replace("_", " ").title())

        # tidy up and rescale
        if self.__container.empty():
            self.axis.set_xlim(left=0, right=100, auto=True)
            self.axis.set_ylim(bottom=0, top=100, auto=True)

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
