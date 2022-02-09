import time
from Helper import Helper

class Message:
    sender = "unknown"
    category = "control"
    content = "string" #string
    rooms = ""
    timeSent = -1 #time

    def __init__(self, sender, category, content, rooms=rooms):
        self.sender = sender
        self.category = category
        self.content = content
        self.rooms = rooms
        self.timeSent = time.asctime( time.localtime(time.time()) )

    def __str__(self):
        # return "Msg: \
        #     \n\tSent: %s\
        #     \n\tFrom: %s\
        #     \n\tType: %s\
        #     \n\tContent: %s\
        #     \n\tRooms: %s" \
        #     % (self.timeSent, self.sender, self.category,
        #     self.content, self.rooms)
        return "[%s][From:%s][Type:%s][Rooms:%s][%s]" % \
            (self.timeSent, self.sender, self.category, self.rooms, self.content)