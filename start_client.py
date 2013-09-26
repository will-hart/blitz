__author__ = 'Will Hart'

import signal
import tornado

from blitz.client import WebApplicationClient

def close_io_loop():
    """Closes an IO loop if sigterm is received"""
    instance = tornado.ioloop.IOLoop.instance()
    instance.add_callback(instance.stop)

signal.signal(signal.SIGTERM, close_io_loop)

if __name__ == "__main__":
    app = WebApplicationClient()
    app.run()
