import traceback
import socket
import threading
import pickle
import datetime
from urllib.parse import uses_relative
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

        while self.server_active:
            # accept connections from outside
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
        
    ###########################################################
    # User and room management
    ###########################################################

    def registerUser(self, address, port, socket, username):
        self.activeUsers[username] = User(address, port, socket, username)
        return username

    def unregisterUser(self, user):
        try:
            self.activeUsers.pop(user)
        except:
            print("%s %s was not found in active user list" % (Helper.STR_ERR, user))
        try:
            for room in self.rooms.keys():
                if user in self.rooms[room]:
                    self.rooms[room].leaveRoom(user)
                    print("%s %s unregistered and removed from %s" % (Helper.STR_INFO, user, room))
        except:
            pass
        return
    
    def addUserToRoom(self, user, room):
        self.rooms[room].joinRoom(user)
        self.activeUsers[user].rooms.append(room)
        # send control message to user to say that they were added to room
        self.sendMessage(
            Message(self.serverName, Helper.MSG_ROOM, Helper.ROOM_JOIN,room),
            self.activeUsers[user].socket
        )
        self.handleTerminalCommands("rooms")
        
    def removeUserFromRoom(self, user, room):
        self.rooms[room].leaveRoom(user)
        self.activeUsers[user].leaveRoom(room)
        # send control message to user to say where removed from room
        self.sendMessage(
            Message(self.serverName, Helper.MSG_ROOM, Helper.ROOM_LEAVE, room),
            self.activeUsers[user].socket
        )
        self.handleTerminalCommands("rooms")

    def createRoom(self, name, creator, desc, canBeDeleted=True):
        self.rooms[name] = Room(name, creator, canBeDeleted)
        self.rooms[name].setDescription(desc)
        self.handleTerminalCommands("rooms")

    ###########################################################
    # Message Receiving and Handling
    ###########################################################

    #await the username submitted by the client
    def listenForUsername(self, clientsocket):
        while self.server_active:
            try:
                message = self.receiveMessage(clientsocket)
                
                if (message.category != Helper.MSG_NAME):
                    print("%s recived odd message while listening for username: %s" % (Helper.STR_ERR, message.category))
                    
                submittedName = message.content
                print("%s Submitted name from %s is %s" % (Helper.STR_INFO, clientsocket.getpeername(), submittedName))

                nameValid = self.isNameValid(submittedName)
                if not nameValid:
                    self.sendMessage(Message(self.serverName, Helper.MSG_NAME, Helper.NAME_INVALID, submittedName),clientsocket)
                    continue

                nameTaken = False
                for user in self.activeUsers.keys():
                    if user == submittedName:
                        nameTaken = True
                        break
                if nameTaken:
                    self.sendMessage(Message(self.serverName, Helper.MSG_NAME, Helper.NAME_USED, submittedName),clientsocket)
                    continue
                else:
                    self.sendMessage(Message(self.serverName, Helper.MSG_NAME, Helper.NAME_VALID, submittedName),clientsocket)
                    return submittedName
            except OSError:
                print("%s Connection for unnamed %s likely closed" % (Helper.STR_WARN, clientsocket.getpeername()))
                return
            except:
                print("Unknown error while obtaining username")
                traceback.print_exc()
                return False

    # listen for messages from a client.
    # this function is run for each client on independant threads
    def listenToClient(self, address, port, clientsocket):
        # obtain username
        username = self.listenForUsername(clientsocket)
        self.registerUser(address, port, clientsocket, username)
        self.addUserToRoom(username, Helper.ROOM_DEFAULT_NAME)    
        
        # at this point, the user is registered, and we are now
        # listening for user-generated messages
        while self.server_active:
            try:
                message = self.receiveMessage(clientsocket)
                # if it is a simple text message, broadcast it to their rooms
                if message.category == Helper.MSG_TEXT:
                    self.broadcast(message)
                    continue
                # if it is not a text message, it is a command
                self.handleUserCommand(message, clientsocket)
            except OSError:
                print("%s Connection for %s likely closed"
                    % (Helper.STR_WARN, username))
                self.unregisterUser(username)
                return

    def receiveMessage(self, usersocket):
        bytes = usersocket.recv(Helper.PACKET_SIZE)
        message = pickle.loads(bytes)
        # print("%s Received %s" % (Helper.STR_INFO, message))
        return message

    ###########################################################
    # Sending messages to clients
    ###########################################################

    def broadcast(self, message):
        toRooms = message.rooms
        # print("going to rooms %s" % toRooms)
        toUsers = []
        for room in toRooms:
            toUsers.extend(self.rooms[room].currentUsers)
        toUsers = list( dict.fromkeys(toUsers) )
        # print("going to users %s" % toUsers)
        for user in toUsers:
            try:
                self.sendMessage(message, self.activeUsers[user].socket)
            except:
                print("%s Unable to broadcast to %s" % (Helper.STR_ERR, user))
                self.unregisterUser(user)

    def whisper(self, message):
        if message.subtype in self.activeUsers.keys():
            targetSocket = self.activeUsers[message.subtype].socket
        else:
            print("%s User tried to whisper person that does not exist" % Helper.STR_INFO)
            sourceSocket = self.activeUsers[message.sender].socket
            self.sendMessage(Message(self.serverName, Helper.MSG_WHISPER, Helper.SIG_FAIL, message.subtype), sourceSocket)
            return
        try:
            self.sendMessage(Message(message.sender, Helper.MSG_WHISPER, Helper.SIG_SUCCESS, message.content), targetSocket)
        except:
            print("Failed to service a whisper")
            sourceSocket = self.activeUsers[message.sender].socket
            self.sendMessage(Message(self.serverName, Helper.MSG_WHISPER, Helper.SIG_FAIL, message.subtype), sourceSocket)
            self.unregisterUser(message.subtype)                

    def sendMessage(self, message, socket):
        messageByte = pickle.dumps(message)
        socket.send(messageByte)
        # print("%s Sent %s" % (Helper.STR_INFO, message))
        return
    
    ###########################################################
    # Command Handling
    ###########################################################

    def handleTerminalCommands(self, text):
        if (text == "help"):
            print("Available commands: 'quit', 'rooms', 'users'")
        if (text == "quit"):
            self.server_active = False
            self.serversocket.close()
            for t in threading.enumerate():
                if (threading.current_thread() != t):
                    t.join()
            print("%s All threads joined. Server program closing gracefully." % Helper.STR_INFO)
            exit(0)
        if (text == "rooms"):
            print ("%s Current rooms and occupants:" % Helper.STR_INFO)
            for room in self.rooms.keys():
                print("|  %s " % room)
                for user in self.rooms[room].currentUsers:
                    print("|    %s" % user)
        if (text == "users"):
            print ("%s Current users:" % Helper.STR_INFO)
            for user in self.activeUsers.keys():
                print("  %s (In rooms: %s)" % (user,", ".join(self.activeUsers[user].rooms)))

    # given a command from a user, handle it appropriately
    def handleUserCommand(self, message, clientsocket):
        # if the user sent a whisper to another client
        if message.category == Helper.MSG_WHISPER:
            self.whisper(message)
        # if the user entered "/info <rooms or users>"
        if message.category == Helper.MSG_INFO:
            # /info rooms -> return list of rooms on the server as a string
            if message.subtype == Helper.INFO_ROOMS:
                roomList = list(self.rooms.keys())
                roomListString = "Rooms on the server are: "
                for room in roomList:
                    roomListString = roomListString + ("%s " % room)
                self.sendMessage(
                    Message(self.serverName, Helper.MSG_INFO, Helper.INFO_ROOMS, roomListString),
                    clientsocket
                )
            # /info users -> return list of users on the server as a string
            if message.subtype == Helper.INFO_USERS:
                if message.content != "":
                    targetRoom = message.content
                    userList = self.rooms[targetRoom].currentUsers
                    userListString = "Currently %s users in room %s: %s" % (len(userList), message.content, ", ".join(userList))
                    self.sendMessage(
                        Message(self.serverName, Helper.MSG_INFO, Helper.INFO_USERS, userListString),
                        clientsocket
                    )
                    return
                userList = list(self.activeUsers.keys())
                userListString = "Currently %s users online: " % (len(userList))
                for user in userList:
                    userListString = userListString + ("%s " % user)
                self.sendMessage(
                    Message(self.serverName, Helper.MSG_INFO, Helper.INFO_USERS, userListString),
                    clientsocket
                )
                return

        # /room <create, join, leave, delete>. Arrives as tuple of (action, room name)
        if (message.category == Helper.MSG_ROOM):
            # if room join is requested
            if message.subtype == Helper.ROOM_JOIN:
                if message.content in self.rooms.keys():
                    if message.sender not in self.rooms[message.content].currentUsers:
                        self.addUserToRoom(message.sender, message.content)
                    else:
                        print("%s User tried to join room they were already in" % Helper.STR_INFO)
                        self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_JOIN, clientsocket)
                else:
                    print("%s User tried to join room that does not exist" % Helper.STR_INFO)
                    self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_JOIN, clientsocket)
            # if room leave is requested
            if message.subtype == Helper.ROOM_LEAVE:
                if message.content in self.rooms.keys():
                    if message.sender in self.rooms[message.content].currentUsers:
                        self.removeUserFromRoom(message.sender, message.content)
                        self.sendMessage(
                            Message(self.serverName, Helper.MSG_ROOM, Helper.ROOM_LEAVE, message.content),
                            clientsocket
                        )
                    else:
                        print("%s User tried to be removed from room they were not in" % Helper.STR_ERR)
                        self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_LEAVE, clientsocket)
                else:
                    print("%s User tried to be removed from room that does not exist" % Helper.STR_ERR)
                    self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_LEAVE, clientsocket)
            # if room creation is requested
            if message.subtype == Helper.ROOM_CREATE:
                isValid = self.isNameValid(message.content)
                if (not isValid):
                    print("%s User tried to create room that had an invalid name" % Helper.STR_ERR)
                    self.sendMessage(Message(self.serverName, Helper.INFO_ROOMS, Helper.ROOM_CREATE, Helper.NAME_INVALID),
                        clientsocket)
                if message.content not in self.rooms.keys():
                    self.createRoom(message.content, message.sender, "A new room")
                    self.sendMessage(
                        Message(self.serverName, Helper.MSG_ROOM, Helper.ROOM_CREATE, message.content),
                        clientsocket)
                else:
                    print("%s User tried to create room that already exists" % Helper.STR_ERR)
                    self.sendCommandFail(Helper.MSG_ROOM, Helper.ROOM_CREATE, clientsocket)
        # if the user says they are leaving
        if message.category == Helper.MSG_QUIT:
            self.unregisterUser(message.sender)
            return

    ###########################################################
    # Helper Functions
    ###########################################################

    #helper method to reduce line length
    def sendCommandFail(self, category, subtype, clientsocket):
        self.sendMessage(Message(self.serverName, category, subtype, Helper.SIG_FAIL),
            clientsocket)

    def isNameValid(self, submittedName):
        if (submittedName == ""):
            return False
        if (len(submittedName) > 16):
            return False
        if (not submittedName.isalnum()):
            return False
        return True
