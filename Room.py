import time

class Room:
    name = "__default__"
    description = "This is a room where we can all listen to eachother."
    createdBy = ""
    createTime = -1
    canBeDeleted = True
    currentUsers = []

    def __init__(self, name, creator, canBeDeleted=True):
        self.name = name
        self.createdBy = creator
        self.createTime = time.asctime( time.localtime(time.time()) )
        if (canBeDeleted is not None):
            self.canBeDeleted = canBeDeleted
        self.currentUsers = []

    def setDescription(self, desc):
        self.description = desc
    
    def joinRoom(self, joiner):
        self.currentUsers.append(joiner)

    def leaveRoom(self, leaver):
        status = False
        if (leaver in self.currentUsers):
            self.currentUsers.remove(leaver)
            status = True
        return status

    def getRoom(self):
        return "%s: created %s by %s" % \
            (self.name, self.createdBy, self.createTime)

    def __str__(self):
        return self.name