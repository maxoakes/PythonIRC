import traceback
import socket
import threading
import pickle
from User import User
from Message import Message
from Room import Room
from Helper import Helper

class Server:    
    server_active = True
    hostname = ""
    port = 7779
    serversocket = False
    serverName = ""
    activeUsers = {}
    rooms = {}

    # init a server. Create socket, listening threads, await text input
    def __init__(self, hostname, port, serverName):
        self.serverName = serverName

        # create an INET, STREAMing socket
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if (self.hostname == ""):
            self.hostname = socket.gethostname()

        if (port):
            self.port = port

        # bind the socket to a public host, and a well-known port
        self.serversocket.bind((hostname, self.port))
        print("Socket Bound: %s:%s" % (hostname, self.port))

        # become a server socket
        self.serversocket.listen()
        
        # spawn thread to listen to connections
        connectionlistening = threading.Thread(target=self.listenForConnections)
        connectionlistening.setName("connectionListener")
        connectionlistening.start()
        
        # terminal loop. Listens to text input via server terminal
        while self.server_active:
            message = input("")
            self.handleTerminalCommands(message)

    # wait for clients to connect and their info to lists
    def listenForConnections(self):

        # create the default room
        self.createRoom(Helper.ROOM_DEFAULT_NAME,self.serverName,"The default room",False)

        print("%s Now listening for new clients in thread" % Helper.STR_INFO)
        while self.server_active:
            # accept connections from outside
            print("%s Awaiting connections..." % Helper.STR_INFO)
            try:
                (clientsocket, address) = self.serversocket.accept()
                userConnectionInfo = (clientsocket, address[0], address[1])
                print("%s Client connected! %s" % (Helper.STR_INFO, address))

                listening = threading.Thread(
                    target=self.listenToClient,
                    args=(userConnectionInfo[1],
                        userConnectionInfo[2],
                        userConnectionInfo[0])
                )
                listening.setName(userConnectionInfo[2])
                listening.start()
            except OSError:
                print("%s Client-listening thread function closing." % Helper.STR_WARN)
                return
        
    # listen for messages from a client.
    # this function is run for each client on independant threads
    def listenToClient(self, address, port, clientsocket):
        # obtain username
        username = self.listenForUsername(clientsocket)

        # add the user to the active user list
        self.registerUser(address, port, clientsocket, username)
        self.addUserToRoom(username, Helper.ROOM_DEFAULT_NAME)
        print("%s Now listening for messages for %s" % (Helper.STR_INFO, username))        
        
        # at this point, the user is registered, and we are now
        # listening for user-generated messages
        while self.server_active:
            try:
                message = self.receiveMessage(clientsocket)
                # if it is a simple text message, broadcast it to their rooms
                if message.messageType == Helper.MSG_TEXT:
                    self.broadcast(message)
                    continue
                # if it is not a text message, it is a command
                self.handleUserCommand(message, clientsocket)
            except OSError:
                print("%s Connection for %s likely closed"
                    % (Helper.STR_WARN, username))
                self.unregisterUser(username)
                return

    #await the username submitted by the client
    def listenForUsername(self, clientsocket):
        while self.server_active:
            try:
                print("%s Listening for username" % Helper.STR_INFO)
                message = self.receiveMessage(clientsocket)
                
                if (message.messageType != Helper.MSG_NAME):
                    print("%s recived odd message: %s" %
                        (Helper.STR_INFO, message.messageType))
                    
                submittedName = message.content
                print("%s Submitted name from %s is %s"
                    % (Helper.STR_INFO, clientsocket.getpeername(), submittedName))

                #check if the username is valid
                nameValid = Helper.isNameValid(submittedName)
                if not nameValid:
                    self.sendMessage(
                        Message(self.serverName, Helper.MSG_NAME, Helper.ACT_INVALID),
                        clientsocket)

                # name is not taken, set client to that username
                # check all usernames to see if the name is taken
                nameTaken = False
                for user in self.activeUsers:
                    if user == submittedName:
                        print("%s Username already in use: %s"
                            % (Helper.STR_WARN, submittedName))
                        nameTaken = True
                        break
                # name is taken, client needs to retry
                if nameTaken:
                    self.sendMessage(
                        Message(self.serverName, Helper.MSG_NAME, Helper.ACT_FAIL),
                        clientsocket)
                # name is not taken, set client to that username
                else:
                    self.sendMessage(
                        Message(
                            self.serverName, Helper.MSG_NAME, Helper.ACT_SUCCESS),
                            clientsocket)
                    return submittedName
            except OSError:
                print("%s Connection for unnamed %s likely closed"
                    % Helper.STR_WAR)
                return
            except:
                print("Unknown error while obtaining username")
                traceback.print_exc()
                return False

    def registerUser(self, address, port, socket, username):
        self.activeUsers[username] = User(address, port, socket, username)
        print("%s new user added to client list" % Helper.STR_INFO)
        return username

    def unregisterUser(self, user):
        try:
            self.activeUsers.pop(user)
        except:
            print("%s %s was not found in active user list" % (Helper.STR_ERR, user))
        try:
            for room in self.rooms.keys():
                self.rooms[room].leaveRoom(user)
                print("%s unregistered and removed from %s" % (user, room))
        except:
            pass
        return

    def broadcast(self, message):
        toRooms = message.rooms
        print("going to rooms %s" % toRooms)
        toUsers = []
        for room in toRooms:
            toUsers.extend(self.rooms[room].currentUsers)
        toUsers = list( dict.fromkeys(toUsers) )
        print("going to users %s" % toUsers)
        for user in toUsers:
            try:
                self.sendMessage(message, self.activeUsers[user].socket)
            except:
                print("%s Unable to broadbase to %s" % (Helper.STR_ERR ,user))
                self.unregisterUser(user)

    def sendMessage(self, messageObject, socket):
        messageByte = pickle.dumps(messageObject)
        socket.send(messageByte)
        print("%s Msg Sent: [%s] %s" %
            (Helper.STR_INFO ,messageObject.messageType, messageObject.content))
        return

    def receiveMessage(self, usersocket):
        bytes = usersocket.recv(Helper.PACKET_SIZE)
        message = pickle.loads(bytes)
        print("%s Received %s" % (Helper.STR_INFO, message))
        return message
    
    def handleTerminalCommands(self, text):
        if (text == "quit"):
            self.server_active = False
            self.serversocket.close()
            for t in threading.enumerate():
                if (threading.current_thread() != t):
                    t.join()
            print("%s All threads joined. Server program closing gracefully." % Helper.STR_INFO)
            exit(0)
        if (text == "rooms"):
            print ("Current rooms and occupants:")
            for room in self.rooms.keys():
                print("  %s " % room)
                for user in self.rooms[room].currentUsers:
                    print("    %s" % user)
        if (text == "users"):
            print ("Current users:")
            for user in self.activeUsers.keys():
                print("  %s $ %s" % (user,self.activeUsers[user].rooms))

    def addUserToRoom(self, user, room):
        self.rooms[room].joinRoom(user)
        self.activeUsers[user].rooms.append(room)
        # send control message to user to say that they were added to room
        self.sendMessage(
            Message(
                self.serverName,
                Helper.MSG_ROOM,
                (Helper.ROOM_JOIN, room)),
            self.activeUsers[user].socket
        )
        print("%s is now in rooms %s" % 
            (self.activeUsers[user], self.activeUsers[user].rooms))
        print("%s now has users:" % (self.rooms[room]))
        for u in self.rooms[room].currentUsers:
            print("  %s" % u)
        
    def removeUserFromRoom(self, user, room):
        self.rooms[room].leaveRoom(user)
        self.activeUsers[user].rooms.remove(room)
        # send control message to user to say where removed from room
        self.sendMessage(
            Message(
                self.serverName,
                Helper.MSG_ROOM,
                (Helper.ROOM_LEAVE, room)),
            self.activeUsers[user].socket
        )
        print("%s is now in rooms %s" % 
            (self.activeUsers[user], self.activeUsers[user].rooms))
        print("%s now has users:" % (self.rooms[room]))
        for u in self.rooms[room].currentUsers:
            print("  %s" % u)

    def createRoom(self, name, creator, desc, canBeDeleted=True):
        self.rooms[name] = Room(name, creator, canBeDeleted)
        self.rooms[name].setDescription(desc)
        self.handleTerminalCommands("rooms")

    # given a command from a user, handle it appropriately
    def handleUserCommand(self, message, clientsocket):
        # if the user entered "/room <something>"
        if message.messageType == Helper.MSG_ROOM:
            # /room list -> return list of rooms on the server as a string
            if message.content == Helper.ROOM_LIST:
                roomList = list(self.rooms.keys())
                roomListString = "Rooms on the server are: "
                for room in roomList:
                    roomListString = roomListString + ("%s " % room)
                self.sendMessage(
                    Message(
                        self.serverName, Helper.MSG_ROOM, (Helper.ROOM_LIST, roomListString)),
                        clientsocket)
                return

            # /room <create, join, leave, delete>. Arrives as tuple of (action, room name)
            if isinstance(message.content, tuple):
                # if room join is requested
                if message.content[0] == "join":
                    if message.content[1] in self.rooms.keys():
                        # the room exists, the user has been added to the room
                        if message.sender not in self.rooms[message.content[1]].currentUsers:
                            self.addUserToRoom(message.sender, message.content[1])
                        else:
                            print("%s User tried to join room they were already in" % Helper.STR_INFO)
                            self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_JOIN, clientsocket)
                    else:
                        self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_JOIN, clientsocket)
                # if room leave is requested
                if message.content[0] == "leave":
                    if message.content[1] in self.rooms.keys():
                        # the user is in the room, the user has been removed from the room
                        if message.sender in self.rooms[message.content[1]].currentUsers:
                            try:
                                self.removeUserFromRoom(message.sender, message.content[1])
                                self.sendMessage(Message(
                                    self.serverName, Helper.MSG_ROOM, (Helper.ROOM_LEAVE, message.content[1])),
                                    clientsocket)
                            except:
                                print("%s Failed to remove user from room" % Helper.STR_ERR)
                                traceback.print_exc()
                                self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_LEAVE, clientsocket)
                        else:
                            print("%s User tried to be removed from room they were not in" % Helper.STR_ERR)
                            self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_LEAVE, clientsocket)
                    else:
                        # the room does not exist
                        self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_LEAVE, clientsocket)

                # if room creation is requested
                if message.content[0] == "create":
                    # if the room does not already exist, create it
                    if message.content[1] not in self.rooms.keys():
                        self.createRoom(message.content[1], message.sender, "A new room")
                        self.sendMessage(Message(
                            self.serverName, Helper.MSG_ROOM, (Helper.ROOM_CREATE, message.content[1])),
                            clientsocket)
                    else:
                        self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_CREATE, clientsocket)
        
        # if the user says they are leaving
        if message.messageType == Helper.MSG_QUIT:
            self.unregisterUser(message.sender)
            return

    #helper method to reduce line length
    def sendCommandFail(self, messageType, subtype, clientsocket):
        self.sendMessage(Message(self.serverName, messageType, (subtype, Helper.ACT_FAIL)),
            clientsocket)
