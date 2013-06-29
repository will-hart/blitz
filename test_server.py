__author__ = 'Will Hart'

from blitz.io.tcp import TcpServer, TcpClient

server = TcpServer(('', 8999))
server.start()

client = TcpClient(("127.0.0.1", 8999))
client.send("From Client")

print "sending"
server.send("Test")

print "sent"
client.disconnect()
server.stop()

print "All done"
