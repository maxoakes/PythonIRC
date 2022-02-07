import time

class User:
    address = ""
    port = -1
    username = "_default_"
    id = -1
    connectTime = -1 #string
    socket = -1 #socket
    rooms = [] #strings

    def __init__(self, address, port, socket, username):
        self.address = address
        self.port = port
        self.socket = socket
        self.connectTime = time.asctime( time.localtime(time.time()) )
        self.id = round(time.time() * 1000)
        self.username = username

    def __str__(self):
        return self.username