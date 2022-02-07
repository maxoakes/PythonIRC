import time
from Codes import Codes

class Message:
    sender = "unknown"
    messageType = "control"
    content = "string" #string
    rooms = ""
    timeSent = -1 #time

    def __init__(self, sender, messageType, content, rooms=rooms):
        self.sender = sender
        self.messageType = messageType
        self.content = content
        self.rooms = rooms
        self.timeSent = time.asctime( time.localtime(time.time()) )

    def __str__(self):
        return "Msg: \
            \n\tSent: %s\
            \n\tFrom: %s\
            \n\tType: %s\
            \n\tContent: %s\
            \n\tRooms: %s" \
            % (self.timeSent, self.sender, self.messageType,
            self.content, self.rooms)