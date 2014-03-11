__author__ = 'Will Hart'

from PySide import QtCore, QtGui

import blitz.communications.signals as sigs


class CalibrationDialog(QtGui.QDialog):
    def __init__(self, steps, minimum, maximum, units, board_id):
        """
        Controls calibration of a board

        :param steps: The number of steps to perform
        :param minimum: The minimum calibration value
        :param maximum: The maximum calibration value
        :param units: The units to use in calibrating the device
        :param board_id: The ID of the board to calibrate
        """

        super(CalibrationDialog, self).__init__()

        # save the defaults
        self.__steps = steps
        self.__minimum = minimum
        self.__maximum = maximum
        self.__units = units
        self.__board_id = board_id

        # calculate constants
        self.__pb_step = 100.0 / self.__steps
        self.__calibration_step = (maximum - minimum) / (self.__steps - 1)
        self.__current_step = 0
        self.__current_value = self.__minimum

        # setup the UI
        self.resize(400, 205)
        self.setModal(True)
        self.progress_bar = QtGui.QProgressBar(self)
        self.progress_bar.setGeometry(QtCore.QRect(10, 10, 381, 23))
        self.progress_bar.setProperty("value", 0)
        self.progress_bar.setTextDirection(QtGui.QProgressBar.TopToBottom)
        self.progress_bar.setObjectName("progressBar")
        self.done_button = QtGui.QPushButton(self)
        self.done_button.setEnabled(False)
        self.done_button.setGeometry(QtCore.QRect(310, 170, 75, 23))
        self.done_button.setDefault(False)
        self.step_button = QtGui.QPushButton(self)
        self.step_button.setGeometry(QtCore.QRect(230, 170, 75, 23))
        self.step_button.setDefault(True)
        self.current_value_label = QtGui.QLabel(self)
        self.current_value_label.setGeometry(QtCore.QRect(10, 40, 381, 121))
        font = QtGui.QFont()
        font.setPointSize(48)
        font.setWeight(75)
        font.setItalic(True)
        font.setBold(True)
        self.current_value_label.setFont(font)
        self.current_value_label.setAlignment(QtCore.Qt.AlignCenter)
        self.setWindowTitle("Calibrate Device")
        self.done_button.setText("Done")
        self.step_button.setText("Calibrate")
        self.current_value_label.setText("{0} {1}".format(self.__current_value, self.__units))

        # connect
        self.done_button.clicked.connect(self.hide_dialog)
        self.step_button.clicked.connect(self.step)

    def hide_dialog(self):
        """
        Hanles when calibration is complete
        """
        self.close()

    def step(self):
        """
        Handles a single calibration step, and updates the UI so the user knows what calibration value to set
        """

        # instruct the board to send a calibration step
        sigs.process_started.send("Sending calibration instruction")
        sigs.board_command_received.send(self.__board_id + "88")

        # update the UI
        self.progress_bar.setValue(self.progress_bar.value() + self.__pb_step)
        self.__current_value += self.__calibration_step
        self.__current_step += 1

        # check if we are done
        if self.__current_step >= self.__steps:
            self.step_button.setEnabled(False)
            self.done_button.setEnabled(True)
            self.current_value_label.setText("Done")
        else:
            self.current_value_label.setText("{0} {1}".format(self.__current_value, self.__units))


class ProcessingDialog(QtGui.QDialog):
    def __init__(self, complete_signal, process_description):
        super(ProcessingDialog, self).__init__()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.resize(370, 120)
        self.setWindowTitle("Processing")
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setGeometry(QtCore.QRect(10, 80, 351, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Close)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.image_screen = QtGui.QLabel(self)
        self.image_screen.setGeometry(QtCore.QRect(10, 20, 51, 51))
        self.image_screen.setObjectName("graphicsView")
        self.movie = QtGui.QMovie("blitz/static/img/loading.gif", QtCore.QByteArray(), self)
        self.movie.setCacheMode(QtGui.QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()
        self.image_screen.setMovie(self.movie)
        self.label = QtGui.QLabel(self)
        self.label.setGeometry(QtCore.QRect(80, 10, 71, 21))
        self.label.setText("Processing")
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setWeight(75)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.processing_description_label = QtGui.QLabel(self)
        self.processing_description_label.setGeometry(QtCore.QRect(80, 30, 281, 51))
        self.processing_description_label.setObjectName("processing_description_label")
        self.processing_description_label.setText(process_description)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.hide_box)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), self.hide_box)
        QtCore.QMetaObject.connectSlotsByName(self)

        # connect to the "close dialog" signal
        complete_signal.connect(self.hide_box)

    def hide_box(self):
        """
        Closes the dialog
        """
        self.close()
