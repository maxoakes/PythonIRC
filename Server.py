import traceback
import socket
import threading
import pickle
from User import User
from Message import Message
from Channel import Channel
from Codes import Codes as OP

class Server:    
    serverAlive = True
    hostname = ""
    port = 7779
    serversocket = False
    serverName = ""
    activeUsers = {}
    channels = {}

    # Init a server. Create socket, listening threads, await text input
    def __init__(self, hostname, port, serverName):
        self.serverName = serverName

        # Create an INET, STREAMing socket
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if (self.hostname == ""):
            self.hostname = socket.gethostname()

        if (port):
            self.port = port

        # Bind the socket to a public host, and a well-known port
        self.serversocket.bind((hostname, self.port))
        print("Socket Bound: %s:%s" % (hostname, self.port))
        self.serversocket.listen()
        
        # Spawn thread to listen to connections
        connectionlistening = threading.Thread(target=self.listenForConnections)
        connectionlistening.setName("connectionListener")
        connectionlistening.start()
        
        # Terminal loop. Listens to text input via server terminal
        while self.serverAlive:
            try:
                message = input("")
                self.handleTerminalCommands(message)
            except KeyboardInterrupt:
                self.fullShutdown()

    # Wait for clients to connect and their info to lists
    def listenForConnections(self):

        # Create the default channel
        self.createChannel(OP.CHANNEL_DEFAULT_NAME,self.serverName,"The default channel",False)

        while self.serverAlive:
            # Accept connections from outside
            try:
                (clientsocket, address) = self.serversocket.accept()
                userConnectionInfo = (clientsocket, address[0], address[1])
                print("%s Client connected! %s" % (OP.STR_INFO, address))

                listening = threading.Thread(
                    target=self.listenToClient,
                    args=(userConnectionInfo[1],
                        userConnectionInfo[2],
                        userConnectionInfo[0])
                )
                listening.setName(userConnectionInfo[2])
                listening.start()
            except OSError:
                print("%s Client-listening thread function closing." % OP.STR_WARN)
                return
            except:
                print("different thread error")
        
    ###########################################################
    # User and channel management
    ###########################################################

    def registerUser(self, address, port, socket, username):
        self.activeUsers[username] = User(address, port, socket, username)
        return username

    def unregisterUser(self, user):
        try:
            self.activeUsers.pop(user)
        except:
            print("%s %s was not found in active user list" % (OP.STR_ERR, user))
        try:
            for channel in self.channels.keys():
                if user in self.channels[channel].currentUsers:
                    self.channels[channel].leaveChannel(user)
                    print("%s %s unregistered and removed from %s" % (OP.STR_INFO, user, channel))
        except:
            pass
        return
    
    def addUserToChannel(self, user, channel):
        self.channels[channel].joinChannel(user)
        self.activeUsers[user].channels.append(channel)
        # Send control message to user to say that they were added to channel
        self.sendMessage(
            Message(self.serverName, OP.MSG_CHANNEL, OP.CHANNEL_JOIN, OP.SIG_SUCCESS, channel),
            self.activeUsers[user].socket
        )
        self.handleTerminalCommands("channels")
        
    def removeUserFromChannel(self, user, channel):
        self.channels[channel].leaveChannel(user)
        self.activeUsers[user].leaveChannel(channel)
        # Send control message to user to say where removed from channel
        self.sendMessage(
            Message(self.serverName, OP.MSG_CHANNEL, OP.CHANNEL_LEAVE, OP.SIG_SUCCESS, channel),
            self.activeUsers[user].socket
        )
        self.handleTerminalCommands("channels")

    def createChannel(self, name, creator, desc, canBeDeleted=True):
        self.channels[name] = Channel(name, creator, canBeDeleted)
        self.channels[name].setDescription(desc)
        self.handleTerminalCommands("channels")

    ###########################################################
    # Message Receiving and Handling
    ###########################################################

    # Await the username submitted by the client
    def listenForUsername(self, clientsocket):
        while self.serverAlive:
            try:
                message = self.receiveMessage(clientsocket)
                
                if (message.category != OP.MSG_NAME):
                    print("%s recived odd message while listening for username: %s" % (OP.STR_ERR, message.category))
                    
                submittedName = message.content
                print("%s Submitted name from %s is %s" % (OP.STR_INFO, clientsocket.getpeername(), submittedName))

                nameValid = self.isNameValid(submittedName)
                if not nameValid:
                    self.sendMessage(
                        Message(self.serverName, OP.MSG_NAME, OP.NO_SUBTYPE, OP.SIG_INVALID, submittedName),
                        clientsocket
                    )
                    continue

                nameTaken = False
                for user in self.activeUsers.keys():
                    if user == submittedName:
                        nameTaken = True
                        break
                if nameTaken:
                    self.sendMessage(
                        Message(self.serverName, OP.MSG_NAME, OP.NO_SUBTYPE, OP.SIG_USED, submittedName),
                        clientsocket
                    )
                    continue
                else:
                    self.sendMessage(
                        Message(self.serverName, OP.MSG_NAME, OP.NO_SUBTYPE, OP.SIG_SUCCESS, submittedName),
                        clientsocket
                    )
                    return submittedName
            except OSError:
                print("%s Connection for unnamed %s likely closed" % (OP.STR_WARN, clientsocket.getpeername()))
                return False
            except:
                print("Unknown error while obtaining username")
                traceback.print_exc()
                return False

    # Listen for messages from a client.
    # This function is run for each client on independant threads
    def listenToClient(self, address, port, clientsocket):
        # Obtain username
        username = self.listenForUsername(clientsocket)
        if not username:
            return
        self.registerUser(address, port, clientsocket, username)
        self.addUserToChannel(username, OP.CHANNEL_DEFAULT_NAME)    
        
        # At this point, the user is registered, and we are now listening for user-generated messages
        while self.serverAlive:
            try:
                message = self.receiveMessage(clientsocket)
                # If it is a simple text message, broadcast it to their channels
                if message.category == OP.MSG_TEXT:
                    self.broadcast(message)
                    continue
                # If it is not a text message, it is a command
                self.handleUserCommand(message, clientsocket)
            except OSError:
                print("%s Connection for %s likely closed" % (OP.STR_WARN, username))
                self.unregisterUser(username)
                return

    # Receive and unpack message
    def receiveMessage(self, usersocket):
        bytes = usersocket.recv(OP.PACKET_SIZE)
        message = pickle.loads(bytes)
        print("%s Received %s" % (OP.STR_INFO, message))
        return message

    ###########################################################
    # Sending messages to clients
    ###########################################################

    # Send a text message to all users that a message's channel list specifies
    def broadcast(self, message):
        toChannels = message.channels
        # print("going to channels %s" % toChannels)
        toUsers = []
        for channel in toChannels:
            toUsers.extend(self.channels[channel].currentUsers)
        toUsers = list( dict.fromkeys(toUsers) )
        # print("going to users %s" % toUsers)
        for user in toUsers:
            try:
                msg = message
                msg.status = OP.SIG_SUCCESS
                self.sendMessage(msg, self.activeUsers[user].socket)
            except:
                print("%s Unable to broadcast to %s" % (OP.STR_ERR, user))
                self.unregisterUser(user)

    # Attempt to send a message from one client to the other
    def whisper(self, message):
        if message.subtype in self.activeUsers.keys():
            targetSocket = self.activeUsers[message.subtype].socket
        else:
            print("%s User tried to whisper person that does not exist" % OP.STR_INFO)
            sourceSocket = self.activeUsers[message.sender].socket
            self.sendMessage(
                Message(self.serverName, OP.MSG_WHISPER, OP.NO_SUBTYPE, OP.SIG_FAIL, message.subtype),
                sourceSocket
            )
            return
        try:
            self.sendMessage(
                Message(message.sender, OP.MSG_WHISPER, OP.NO_SUBTYPE, OP.SIG_SUCCESS, message.content),
                targetSocket
            )
        except:
            print("Failed to service a whisper")
            sourceSocket = self.activeUsers[message.sender].socket
            self.sendMessage(
                Message(self.serverName, OP.MSG_WHISPER, OP.NO_SUBTYPE, OP.SIG_FAIL, message.subtype),
                sourceSocket
            )
            self.unregisterUser(message.subtype)                

    # Package and send message to destination client
    def sendMessage(self, message, socket):
        messageByte = pickle.dumps(message)
        socket.send(messageByte)
        print("%s Sent %s" % (OP.STR_INFO, message))
        return
    
    ###########################################################
    # Command Handling
    ###########################################################

    # Parse text into the server's terminal
    def handleTerminalCommands(self, text):
        match text:
            case "help":
                print("Available commands: 'quit', 'channels', 'users'")
            case "quit":
                self.fullShutdown()
            case "channels":
                print ("%s Current channels and occupants:" % OP.STR_INFO)
                for channel in self.channels.keys():
                    print("|  %s " % channel)
                    for user in self.channels[channel].currentUsers:
                        print("|    %s" % user)
            case "users":
                print ("%s Current users:" % OP.STR_INFO)
                for user in self.activeUsers.keys():
                    print("  %s (In channels: %s)" % (user,", ".join(self.activeUsers[user].channels)))
            case _:
                print ("Not a command. Type 'help' for list of commands")

    # Given a command from a user, handle it appropriately
    def handleUserCommand(self, message, clientsocket):
        match message.category:
            # Message is a whisper to another client
            case OP.MSG_WHISPER:
                self.whisper(message)
            # Message is a request for an action on a channel
            case OP.MSG_INFO:
                match message.subtype:
                    # /info channels -> return list of channels on the server as a string
                    case OP.INFO_CHANNELS:
                        channelList = list(self.channels.keys())
                        channelListString = "Channels on the server are: "
                        for channel in channelList:
                            channelListString = channelListString + ("%s " % channel)
                        self.sendMessage(
                            Message(self.serverName, OP.MSG_INFO, OP.INFO_CHANNELS, OP.SIG_SUCCESS, channelListString),
                            clientsocket
                        )
                    # /info users -> return list of users on the server as a string
                    case OP.INFO_USERS:
                        if message.content != "":
                            targetChannel = message.content
                            if targetChannel not in self.channels.keys():
                                failString = "Channel %s does not exist" % message.content
                                self.sendMessage(
                                Message(self.serverName, OP.MSG_INFO, OP.INFO_USERS, OP.SIG_FAIL, failString),
                                    clientsocket
                                )
                                return
                            userList = self.channels[targetChannel].currentUsers
                            userListString = "Currently %s users in channel %s: %s" % (len(userList), message.content, ", ".join(userList))
                            self.sendMessage(
                                Message(self.serverName, OP.MSG_INFO, OP.INFO_USERS, OP.SIG_SUCCESS, userListString),
                                clientsocket
                            )
                            return
                        userList = list(self.activeUsers.keys())
                        userListString = "Currently %s users online: " % (len(userList))
                        for user in userList:
                            userListString = userListString + ("%s " % user)
                        self.sendMessage(
                            Message(self.serverName, OP.MSG_INFO, OP.INFO_USERS, OP.SIG_SUCCESS, userListString),
                            clientsocket
                        )
                        return
            # /channel <create, join, leave, delete>
            case OP.MSG_CHANNEL:
                match message.subtype:
                    # A channel join was requested
                    case OP.CHANNEL_JOIN:
                        if message.content in self.channels.keys():
                            if message.sender not in self.channels[message.content].currentUsers:
                                self.addUserToChannel(message.sender, message.content)
                            else:
                                print("%s User tried to join channel they were already in" % OP.STR_INFO)
                                self.sendCommandFail(OP.MSG_CHANNEL, OP.CHANNEL_JOIN, message.content, clientsocket)
                        else:
                            print("%s User tried to join channel that does not exist" % OP.STR_INFO)
                            self.sendCommandFail(OP.MSG_CHANNEL, OP.CHANNEL_JOIN, message.content, clientsocket)
                    # A channel leave was requested
                    case OP.CHANNEL_LEAVE:
                        if message.content in self.channels.keys():
                            if message.sender in self.channels[message.content].currentUsers:
                                self.removeUserFromChannel(message.sender, message.content)
                                self.sendMessage(
                                    Message(self.serverName, OP.MSG_CHANNEL, OP.CHANNEL_LEAVE, OP.SIG_SUCCESS, message.content),
                                    clientsocket
                                )
                            else:
                                print("%s User tried to be removed from channel they were not in" % OP.STR_ERR)
                                self.sendCommandFail(OP.MSG_CHANNEL, OP.CHANNEL_LEAVE, message.content, clientsocket)
                        else:
                            print("%s User tried to be removed from channel that does not exist" % OP.STR_ERR)
                            self.sendCommandFail(OP.MSG_CHANNEL, OP.CHANNEL_LEAVE, message.content, clientsocket)
                    # A channel creation was requested
                    case OP.CHANNEL_CREATE:
                        isValid = self.isNameValid(message.content)
                        if (not isValid):
                            print("%s User tried to create channel that had an invalid name" % OP.STR_ERR)
                            self.sendMessage(
                                Message(self.serverName, OP.INFO_CHANNELS, OP.CHANNEL_CREATE, OP.SIG_INVALID, message.content),
                                clientsocket)
                        if message.content not in self.channels.keys():
                            self.createChannel(message.content, message.sender, "A new channel")
                            self.sendMessage(
                                Message(self.serverName, OP.MSG_CHANNEL, OP.CHANNEL_CREATE, OP.SIG_SUCCESS, message.content),
                                clientsocket)
                        else:
                            print("%s User tried to create channel that already exists" % OP.STR_ERR)
                            self.sendCommandFail(OP.MSG_CHANNEL, OP.CHANNEL_CREATE, message.content, clientsocket)
                    # Deletion of a channel is requested
                    case OP.CHANNEL_DELETE:
                        isValid = self.isNameValid(message.content)
                        if message.content not in self.channels.keys():
                            print("%s User tried to delete a channel that does not exist" % OP.STR_ERR)
                            self.sendCommandFail(OP.MSG_CHANNEL, OP.CHANNEL_DELETE, message.content, clientsocket)
                            return
                        if (not isValid):
                            print("%s User tried to delete a channel that had an invalid name" % OP.STR_ERR)
                            self.sendMessage(
                                Message(self.serverName, OP.INFO_CHANNELS, OP.CHANNEL_CREATE, OP.SIG_INVALID, message.content),
                                clientsocket)
                            return
                        if len(self.channels[message.content].currentUsers) > 0:
                            print("%s User tried to delete a channel that still had clients in it" % OP.STR_ERR)
                            self.sendCommandFail(OP.MSG_CHANNEL, OP.CHANNEL_DELETE, message.content, clientsocket)
                            return
                        if (not self.channels[message.content].canBeDeleted):
                            print("%s User tried to delete a channel that is not allowed to be deleted" % OP.STR_ERR)
                            self.sendCommandFail(OP.MSG_CHANNEL, OP.CHANNEL_DELETE, message.content, clientsocket)
                            return
                        else:
                            del self.channels[message.content]
                            print("%s The channel %s was deleted via client request" % (OP.STR_INFO, message.content))
                            self.sendMessage(
                                Message(self.serverName, OP.MSG_CHANNEL, OP.CHANNEL_DELETE, OP.SIG_SUCCESS, message.content),
                                clientsocket)
            # A client says they are leaving
            case OP.MSG_QUIT:
                self.unregisterUser(message.sender)
                return

    ###########################################################
    # Helper Functions
    ###########################################################

    # Helper method to reduce line length
    def sendCommandFail(self, category, subtype, content, clientsocket):
        self.sendMessage(Message(self.serverName, category, subtype, OP.SIG_FAIL, content),
            clientsocket)

    # Check if a string entered by a user is valid as a username or channel name
    def isNameValid(self, submittedName):
        if (submittedName == ""):
            return False
        if (len(submittedName) > 16):
            return False
        if (not submittedName.isalnum()):
            return False
        return True

    # Gracefully kick out all users and close this application
    def fullShutdown(self):
        self.serverAlive = False
        usersToRemove = []
        for user in self.activeUsers.keys():
            usersToRemove.append(user)
        for user in usersToRemove:
            try:
                print("%s closing socket for %s" % (OP.STR_INFO, user))
                self.activeUsers[user].socket.shutdown(socket.SHUT_RDWR)
                self.activeUsers[user].socket.close()
                print("%s ^ closed" % OP.STR_INFO)
            except:
                print("f")
        self.serversocket.close()

        print("%s All threads joined. Server program closing gracefully." % OP.STR_INFO)
        return

