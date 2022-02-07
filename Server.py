import traceback
import socket
import threading
import pickle
from User import User
from Message import Message
from Room import Room
from Codes import Codes

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
        connectionlistening = threading.Thread(
            target=self.listenForConnections
        )
        connectionlistening.setName("connectionListener")
        connectionlistening.start()
        
        #terminal loop. Listens to text input via server terminal
        while self.server_active:
            message = input("")
            self.handleCommand(message)

    # wait for clients to connect and their info to lists
    def listenForConnections(self):

        #create the default room
        self.rooms[Codes.ROOM_DEFAULT_NAME] = \
            Room(Codes.ROOM_DEFAULT_NAME,self.serverName,False)
        self.rooms[Codes.ROOM_DEFAULT_NAME].setDescription("The default room")

        print("%s Now listening for new clients in thread" % Codes.STR_INFO)
        while self.server_active:
            # accept connections from outside
            print("%s Awaiting connections..." % Codes.STR_INFO)
            try:
                (clientsocket, address) = self.serversocket.accept()
                userConnectionInfo = (clientsocket, address[0], address[1])
                print("%s Client connected! %s" % (Codes.STR_INFO, address))

                listening = threading.Thread(
                    target=self.listenToClient,
                    args=(userConnectionInfo[1],
                        userConnectionInfo[2],
                        userConnectionInfo[0])
                )
                listening.setName(userConnectionInfo[2])
                listening.start()
            except OSError:
                print("%s Client-listening thread function closing." % Codes.STR_WARN)
                return
        
    #listen for messages from client after getting a username from them
    def listenToClient(self, address, port, clientsocket):
        #obtain username
        username = self.listenForUsername(clientsocket)
        if (not username):
            print("error status returned in username")
            self.unregisterUser(username)
            return

        #add the user to the active user list
        self.registerUser(address, port, clientsocket, username)
        print("%s Now listening for messages for %s"
            % (Codes.STR_INFO, username))

        # put new user in default room
        self.addUserToRoom(username, Codes.ROOM_DEFAULT_NAME)
        
        while self.server_active:
            try:
                message = self.receiveMessage(clientsocket)
                #if it is a simple text message, broadcast it to their rooms
                if message.messageType == Codes.MSG_TEXT:
                    self.broadcast(message)
                    continue
                #if it is not a text message, it is a command
                if message.messageType == Codes.MSG_ROOM:
                    if message.content == Codes.ROOM_LIST:
                        roomList = list(self.rooms.keys())
                        self.sendMessage(
                            Message(
                                self.serverName, Codes.MSG_ROOM, (Codes.ROOM_LIST, roomList)),
                                clientsocket)
                        continue
                    if isinstance(message.content, tuple):
                        # if room join is requested
                        if message.content[0] == "join":
                            if message.content[1] in self.rooms.keys():
                                self.addUserToRoom(message.sender, message.content[1])
                            else:
                                self.sendMessage(Message(
                                    self.serverName, Codes.MSG_ROOM, (Codes.ROOM_JOIN, Codes.ACT_FAIL)),
                                    clientsocket)

                        # if room leave is requested
                        if message.content[0] == "leave":
                            if message.content[1] in self.rooms.keys():
                                if message.sender in self.rooms[message.content[1]]:
                                    try:
                                        self.rooms[message.content[1]].remove(message.sender)
                                    except:
                                        print("%s Failed to remove user from room" % Codes.STR_ERR)
                                        self.sendMessage(Message(
                                            self.serverName, Codes.MSG_ROOM, (Codes.ROOM_LEAVE, Codes.ACT_FAIL)),
                                            clientsocket)
                                else:
                                    print("%s User tried to be removed from room they were not in" % Codes.STR_ERR)
                                    self.sendMessage(Message(
                                        self.serverName, Codes.MSG_SIG, Codes.ACT_FAIL),
                                        clientsocket)
                            else:
                                self.sendMessage(Message(
                                    self.serverName, Codes.MSG_SIG, Codes.ACT_FAIL),
                                    clientsocket)

                        # if room creation is requested
                        if message.content[0] == "create":
                            if message.content[1] not in self.rooms.keys():
                                self.createRoom(message.content[1], message.sender, "A new room")
                                self.sendMessage(Message(
                                    self.serverName, Codes.MSG_SIG, Codes.ACT_SUCCESS),
                                    clientsocket)
                            else:
                                self.sendMessage(Message(
                                    self.serverName, Codes.MSG_SIG, Codes.ACT_FAIL),
                                    clientsocket)
                                
                if message.messageType == Codes.MSG_QUIT:
                    self.unregisterUser(username)
                    return
            except OSError:
                print("%s Connection for %s likely closed"
                    % (Codes.STR_WARN, username))
                self.unregisterUser(username)
                return

    def listenForUsername(self, clientsocket):
        while self.server_active:
            try:
                print("%s Listening for username" % Codes.STR_INFO)
                message = self.receiveMessage(clientsocket)
                
                if (message.messageType != Codes.MSG_NAME):
                    print("%s recived odd message: %s" %
                        (Codes.STR_INFO, message.messageType))
                    
                submittedName = message.content
                print("%s Submitted name from %s is %s"
                    % (Codes.STR_INFO, clientsocket.getpeername(), submittedName))

                #check all usernames to see if the name is taken
                nameTaken = False
                for user in self.activeUsers:
                    if user == submittedName:
                        print("%s Username already in use: %s"
                            % (Codes.STR_WARN, submittedName))
                        nameTaken = True
                        break
                #name is taken, client needs to retry
                if nameTaken:
                    self.sendMessage(
                        Message(self.serverName, Codes.MSG_SIG, False),
                        clientsocket)
                #name is not taken, set client to that username
                else:
                    self.sendMessage(
                        Message(
                            self.serverName, Codes.MSG_SIG, True),
                            clientsocket)
                    return submittedName
            except OSError:
                print("%s Connection for unnamed %s likely closed"
                    % Codes.STR_WAR)
                return
            except:
                print("Unknown error while obtaining username")
                traceback.print_exc()
                return False

    def registerUser(self, address, port, socket, username):
        self.activeUsers[username] = User(address, port, socket, username)
        print("%s new user added to client list" % Codes.STR_INFO)
        return username

    def unregisterUser(self, user):
        try:
            self.activeUsers.pop(user)
            print("%s unregestered" % user)
            return
        except :
            print("%s %s was not found in active user list"
                % (Codes.STR_ERR, user))

    def broadcast(self, message):
        toRooms = message.rooms
        print("going to rooms %s" % toRooms)
        toUsers = []
        for room in toRooms:
            toUsers.extend(self.rooms[room].users)
        print("going to users %s" % toUsers)
        for user in toUsers:
            try:
                self.sendMessage(message, self.activeUsers[user].socket)
            except:
                print("%s Unable to broadbase to %s" % (Codes.STR_ERR ,user))
                self.unregisterUser(user)

    def sendMessage(self, messageObject, socket):
        messageByte = pickle.dumps(messageObject)
        socket.send(messageByte)
        print("%s Msg Sent: [%s] %s" %
            (Codes.STR_INFO ,messageObject.messageType, messageObject.content))
        return

    def receiveMessage(self, usersocket):
        bytes = usersocket.recv(Codes.PACKET_SIZE)
        message = pickle.loads(bytes)
        print("%s Received %s" % (Codes.STR_INFO, message))
        return message
    
    def handleCommand(self, text):
        if (text == "quit"):
            self.server_active = False
            self.serversocket.close()
            for t in threading.enumerate():
                if (threading.current_thread() != t):
                    t.join()
            print("%s All threads joined. Server program closing gracefully." % Codes.STR_INFO)
            exit(0)

    def addUserToRoom(self, user, room):
        self.rooms[room].joinRoom(user)
        self.activeUsers[user].rooms.append(room)
        #send control message to user to say that they were added to room
        self.sendMessage(
            Message(
                self.serverName,
                Codes.MSG_ROOM,
                (Codes.ROOM_JOIN, room)),
            self.activeUsers[user].socket
        )
        print("%s is now in rooms %s" % 
            (self.activeUsers[user], self.activeUsers[user].rooms))
        print("%s now has users:" % (self.rooms[room]))
        for u in self.rooms[room].users:
            print("  %s" % u)

    def createRoom(self, name, creator, desc):
        self.rooms[name] = Room(name, creator)
        self.rooms[name].setDescription(desc)