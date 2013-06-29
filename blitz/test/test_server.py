__author__ = 'Will Hart'

__doc__= """
A simple script for debugging the TCP client / server
"""

from blitz.io.tcp import TcpClient, TcpServer
import time

# set up objects
server = TcpServer(8999)
client = TcpClient("127.0.0.1", 8999)
print ""

# wait then send ACK from server
time.sleep(1)
server._send("NACK")
print ""

# start logging
time.sleep(2)
client.request_start()

# clean up
time.sleep(2)
client.disconnect()
server.shutdown()
