import time
from Codes import Codes as OP

class User:
    address = OP.NOT_INIT #string
    port = OP.NOT_INIT #int
    username = OP.NOT_INIT #string
    id = OP.NOT_INIT #int
    connectTime = OP.NOT_INIT #string
    socket = OP.NOT_INIT #socket object
    channels = OP.NOT_INIT #list of strings

    def __init__(self, address, port, socket, username):
        self.address = address
        self.port = port
        self.socket = socket
        self.connectTime = time.asctime( time.localtime(time.time()) )
        self.id = round(time.time() * 1000)
        self.username = username
        self.channels = []

    def leaveChannel(self, channel):
        status = False
        if (channel in self.channels):
            self.channels.remove(channel)
            status = True
        return status

    def __str__(self):
        return self.username