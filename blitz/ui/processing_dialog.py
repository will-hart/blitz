from PySide import QtCore, QtGui


class ProcessingDialog(QtGui.QDialog):
    def __init__(self, complete_signal, process_description):
        super(ProcessingDialog, self).__init__()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.resize(370, 120)
        self.setWindowOpacity(0.8)
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
