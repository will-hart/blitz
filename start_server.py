__author__ = 'Will Hart'

import signal
import time

from blitz.server import Application

app = None

def run_app():
    app = Application()

    while app.is_running:
        # just check periodically if we should exit
        time.sleep(0.5)

def do_shutdown():
    app.shutdown()

signal.signal(signal.SIGTERM, do_shutdown)

run_app()
