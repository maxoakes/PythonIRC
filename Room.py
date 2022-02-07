import time

class Room:
    name = "__default__"
    description = "This is a room where we can all listen to eachother."
    createdBy = ""
    createTime = -1
    canBeDeleted = True
    users = []

    def __init__(self, name, creator, canBeDeleted=canBeDeleted):
        self.name = name
        self.createdBy = creator
        self.createTime = time.asctime( time.localtime(time.time()) )
        if (canBeDeleted is not None):
            self.canBeDeleted = canBeDeleted

    def setDescription(self, desc):
        self.description = desc
    
    def joinRoom(self, joiner):
        self.users.append(joiner)

    def leaveRoom(self, leaver):
        status = False
        for user in self.users:
            if leaver.username == user.username:
                self.users.remove(user)
                status = True
                break
        return status

    def getRoom(self):
        return "%s: created %s by %s" % \
            (self.name, self.createdBy, self.createTime)

    def __str__(self):
        return self.name