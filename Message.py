from datetime import datetime
from Helper import Helper

class Message:
    sender = Helper.NOT_INIT
    category = Helper.NOT_INIT
    subtype = Helper.NOT_INIT
    content = Helper.NOT_INIT
    rooms = Helper.NOT_INIT
    timeSent = Helper.NOT_INIT

    def __init__(self, sender, category, subtype, content, rooms=rooms):
        self.sender = sender
        self.category = category
        self.content = content
        self.subtype = subtype
        self.rooms = rooms
        self.timeSent = datetime.now().strftime("%H:%M:%S")

    def __str__(self):
        rooms = ",".join(self.rooms)
        return "[T=%s][S=%s][T=%s:%s][R=%s][C=%s]" % \
            (self.timeSent, self.sender, self.category, self.subtype, rooms, self.content)

    # text
    # username
    # room
    #   join
    #   leave
    #   create
    # quit
    # signal
    #   success
    #   fail
    #   invalid
    # info
    #   users
    #   rooms