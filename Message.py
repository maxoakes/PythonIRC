from datetime import datetime
from Helper import Helper

class Message:
    sender = Helper.NOT_INIT
    category = Helper.NOT_INIT
    subtype = Helper.NOT_INIT
    status = Helper.NOT_INIT
    content = Helper.NOT_INIT
    rooms = Helper.NOT_INIT
    timeSent = Helper.NOT_INIT

    def __init__(self, sender, category, subtype, status, content, rooms=rooms):
        self.sender = sender
        self.category = category
        self.content = content
        self.subtype = subtype
        self.status = status
        self.rooms = rooms
        self.timeSent = datetime.now().strftime("%H:%M:%S")
        

    def __str__(self):
        rooms = ",".join(self.rooms)
        return "[T=%s][S=%s][T=%s:%s][X=%s][R=%s][C=%s]" % \
            (self.timeSent, self.sender, self.category, self.subtype, self.status, rooms, self.content)