import traceback
import socket
import threading
import pickle
from User import User
from Message import Message
from Codes import Codes

class Server:
    SIZE = 4096
    
    server_active = True
    hostname = ""
    port = 7779
    serversocket = False
    serverName = ""
    activeUsers = []
    rooms = []

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
        print("%s Now listening for new clients in thread" % Codes.STR_INFO)
        while self.server_active:
            # accept connections from outside
            print("%s Awaiting connections..." % Codes.STR_INFO)
            try:
                #clientsocket is type socket
                #address[0] is IP address
                #address[1] is port number
                (clientsocket, address) = self.serversocket.accept()

                print("%s Client connected! %s" % (Codes.STR_INFO, address))
                newUser = self.registerUser(address[0],address[1],clientsocket)

                listening = threading.Thread(
                    target=self.listenToClient,
                    args=(newUser,)
                )
                listening.setName(address[1])
                listening.start()
            except OSError:
                print("%s Client-listening thread function closing." % Codes.STR_WARN)
                return
        

    def listenToClient(self, user):
        # address = IPv4
        # port = port num
        # username = string
        # id = time in ms
        # connectTime = formatted string
        status = self.listenForUsername(user)
        if (not status):
            self.unregisterUser(user)
            return
        print("%s Now listening for messages for %s"
            % (Codes.STR_INFO, user.username)
        )
        while self.server_active:
            try:
                message = self.receiveMessage(user.socket)
                if message.messageType == Codes.MSG_TEXT:
                    
                    self.broadcast(message)
                if message.messageType == Codes.MSG_ROOM:
                    print(message.content)
                if message.messageType == Codes.MSG_QUIT:
                    self.unregisterUser(user)
                    return
            except OSError:
                print("%s Connection for %s likely closed"
                    % (Codes.STR_WARN, user.username))
                self.unregisterUser(user)
                return

    def listenForUsername(self, user):
        while self.server_active:
            try:
                print("[INFO] Listening for username from", user.address)
                message = self.receiveMessage(user.socket)
                if (message.messageType != Codes.MSG_NAME):
                    assert Exception("Unexpected message from client")
                submittedName = message.content
                print("%s Submitted name from %s is %s"
                    % (Codes.STR_INFO, user.address, submittedName))

                #check all usernames to see if the name is taken
                nameTaken = False
                for u in self.activeUsers:
                    if u.username == submittedName:
                        print("%s Username already in use: %s"
                            % (Codes.STR_WARN, submittedName))
                        nameTaken = True
                        break
                #name is taken, client needs to retry
                if nameTaken:
                    self.sendMessage(
                        Message(self.serverName,
                            Codes.MSG_SIG,
                            False), user.socket
                        )
                #name is not taken, set client to that username
                else:
                    user.username = submittedName
                    self.sendMessage(
                        Message(
                            self.serverName,
                            Codes.MSG_SIG,
                            True
                        ), user.socket)
                    return True
            except OSError:
                print("%s Connection for %s likely closed"
                    % (Codes.STR_WARN, user.username))
                self.unregisterUser(user.address[0])
                return
            except:
                return False


    def broadcast(self, message):
        print("Broadcasting...")
        for user in self.activeUsers:
            try:
                self.sendMessage(message, user.socket)
            except:
                print("%s Unable to broadbase to %s"
                    % (Codes.STR_ERR ,user.username))
                self.unregisterUser(user.address)

    def registerUser(self, address, port, socket):
        newUser = User(address, port, socket)
        self.activeUsers.append(newUser)
        print("%s new user added to client list" % Codes.STR_INFO)
        return newUser

    def unregisterUser(self, user):
        for u in self.activeUsers:
            if u is user:
                try:
                    self.activeUsers.remove(user)
                    print(user.username + " unregestered")
                    return
                except ValueError:
                    print("%s %s was not found in active user list"
                        % (Codes.STR_ERR, user.username))

    def sendMessage(self, messageObject, socket):
        messageByte = pickle.dumps(messageObject)
        socket.send(messageByte)
        print("%s Message Sent: [%s] %s" %
            (Codes.STR_INFO ,messageObject.messageType, messageObject.content))
        return

    def receiveMessage(self, usersocket):
        bytes = usersocket.recv(self.SIZE)
        message = pickle.loads(bytes)
        print(
            "[INFO] Message Received:",
            "\n\tSent", message.timeSent,
            "\n\tFrom", message.sender,
            "\n\tType", message.messageType,
            "\n\tContent", message.content
        )
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
        if (text == "list"):
            for u in self.activeUsers:
                print(u.username,u.address)
        if (text == "bfm"):
            text = text[3:]
            commandList = text.split(" ")
            self.bruteForceMessage(commandList[1],commandList[2])
    
    def bruteForceMessage(self, messageType, content, user):
        target = False
        for u in self.activeUsers:
            if u.username == user:
                target = u
        self.sendMessage(Message("Server", messageType, content), target.socket)
