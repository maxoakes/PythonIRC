import time

class Room:
    name = "__default__"
    description = "This is a room where we can all listen to eachother."
    createdBy = ""
    createTime = -1
    users = []

    def __init__(self, name, creator):
        self.name = name
        self.createdBy = creator
        self.createTime = time.asctime( time.localtime(time.time()) )

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