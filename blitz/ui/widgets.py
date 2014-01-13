from datetime import datetime

from PySide import QtGui as Qt

import blitz.communications.signals as sigs


class BlitzSessionWidget(Qt.QWidget):
    """
    Creates a session widget for displaying and downloading sessions from the data logger
    """

    def __init__(self, session_id, timestamp_started, number_of_items, available):
        """
        Creates a new widget and populates it

        :param session_id: the number of the session
        :param timestamp_started: the timestamp when this session began
        :param number_of_items: the number of items logged in the session
        :param available: True if the session has already been downloaded, False otherwise
        """

        super(BlitzSessionWidget, self).__init__()

        # save required variables
        self.session_id = session_id
        self.date_started = datetime.fromtimestamp(timestamp_started / 1000)
        self.number_of_items = number_of_items
        self.available = available

        # set up the widget boundaries
        self.resize(450, 80)
        sizePolicy = Qt.QSizePolicy(Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        # colour the background
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.QColor(255, 255, 255))
        self.setPalette(palette)

        # create the layout grid
        self.grid = Qt.QGridLayout(self)

        # button for viewing sessions in the application
        self.view_button = Qt.QPushButton("View")
        self.view_button.setEnabled(self.available)
        self.grid.addWidget(self.view_button, 0, 2, 1, 1)

        # button for downloading session information from the data logger
        self.download_button = Qt.QPushButton("Download")
        self.download_button.setEnabled(not self.available)
        self.download_button.triggered.connect(self.download_button_clicked)
        self.grid.addWidget(self.download_button, 1, 2, 1, 1)

        # label displaying the session ID
        self.session_value_label = Qt.QLabel(str(self.session_id))
        font = Qt.QFont()
        font.setPointSize(14)
        font.setWeight(75)
        font.setBold(True)
        self.session_value_label.setFont(font)
        self.grid.addWidget(self.session_value_label, 0, 1, 1, 1)

        # A header for sessions
        self.session_title_label = Qt.QLabel("Session ")
        self.session_title_label.setFont(font)
        self.grid.addWidget(self.session_title_label, 0, 0, 1, 1)

        # a label displaying session information
        self.session_description_label = Qt.QLabel("%s items logged" % self.number_of_items)
        self.grid.addWidget(self.session_description_label, 1, 0, 1, 2)

        # a label displaying the time the session started
        self.session_date_label = Qt.QLabel("Started %s" % self.date_started.isoformat((" ")))
        self.grid.addWidget(self.session_date_label, 2, 0, 1, 2)

        # set the layout to the grid
        self.setLayout(self.grid)

    def download_button_clicked(self):
        """
        When the "download" button is clicked, send a download request to the client application
        """
        sigs.client_requested_download.send(self.session_id)
