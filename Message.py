import time

class Message:
    sender = "unknown"
    messageType = "control"
    content = "string"
    timeSent = -1

    def __init__(self, sender, messageType, content):
        self.sender = sender
        # command, chat, signal, username
        self.messageType = messageType
        self.content = content
        self.timeSent = time.asctime( time.localtime(time.time()) )