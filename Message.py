from datetime import datetime
from Codes import Codes as OP

class Message:
    sender = OP.NOT_INIT #string
    category = OP.NOT_INIT #string
    subtype = OP.NOT_INIT #string
    status = OP.NOT_INIT #string
    content = OP.NOT_INIT #string
    channels = OP.NOT_INIT #list of string
    timeSent = OP.NOT_INIT #string

    def __init__(self, sender, category, subtype, status, content, channels=channels):
        self.sender = sender
        self.category = category
        self.content = content
        self.subtype = subtype
        self.status = status
        self.channels = channels
        self.timeSent = datetime.now().strftime("%H:%M:%S")
        

    def __str__(self):
        channels = ",".join(self.channels)
        return "[Ti=%s][Se=%s][Ty=%s:%s][Sig=%s][Ch=%s][Co=%s]" % \
            (self.timeSent, self.sender, self.category, self.subtype, self.status, channels, self.content)