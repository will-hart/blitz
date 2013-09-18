__author__ = 'Will Hart'

import gtk

from blitz.ui.Windows import MainBlitzWindow


class LoggerWindow(MainBlitzWindow):
    def __init__(self):
        super(LoggerWindow, self).__init__()


if __name__ == "__main__":

    # create the logger
    app = LoggerWindow()
    gtk.main()
