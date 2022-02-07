import socket
import threading
import pickle
from Message import Message
from Codes import Codes

class Client:
    username = Codes.NOT_INIT
    mySocket = False
    rooms = []

    def __init__(self, destination, port, username):
        self.username = username

        # create an INET, STREAMing socket
        self.mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.mySocket.connect((destination, port))
        except ConnectionRefusedError:
            print ("Connection Refused. Closing...")
            return

        print("Connected to %s:%s" % (destination, port))
        if (not self.login()):
            print("Halting...")
            return

        self.awaitRoomEntry()

        # spawn listening thread
        listening = threading.Thread(target = self.listenForMessage)
        listening.start()

        #terminal input loop
        while self.mySocket:
            try:
                text = input("") #await keyboard input
                text = text.strip()
                # it is a blank input
                if (text == ""):
                    continue
                # is it a command
                if (text[0] == '/'):
                    text = text[1:]
                    self.handleCommand(text)
                    continue
                #it is a chat message
                self.sendMessage(
                    Message(self.username,
                        Codes.MSG_TEXT,
                        text,
                        rooms=self.rooms))
            except ConnectionResetError:
                return self.gracefulClose()
            except KeyboardInterrupt:
                self.handleCommand("quit")
                print("Telling server of closing connection...")
                return

    # thread function for listening for messages from server
    def listenForMessage(self):
        while self.mySocket:
            try:
                message = self.receiveMessage()
                # we have an update on rooms
                if (message.messageType == Codes.MSG_ROOM):
                    print("room message received")
                    #print room list from server
                    if (message.content[0] == Codes.ROOM_LIST and message.content[1]):
                        print(message.content[1])
                    #join room successful
                    if (message.content[0] == Codes.ROOM_JOIN and message.content[1]):
                        print("Successfully joined %s" % message.content[1])
                        self.rooms.append(message.content[1])
                    #create room successful
                    if (message.content[0] == Codes.ROOM_CREATE and message.content[1]):
                        print("Successfully created %s" % message.content[1])
                    elif (not message.content[1]):
                        print("room action failed")

            except socket.timeout:
                pass
            except (OSError, ConnectionResetError):
                return self.gracefulClose()

    # input a username and submit it to the server
    def login(self):
        while self.mySocket:
            submitted = input("Choose a username: ")
            try:
                self.sendMessage(
                    Message(
                        self.username,
                        Codes.MSG_NAME,
                        submitted))
                print("awaiting response")
                message = self.receiveMessage()
                status = message.content
                if status: #username accepted
                    print ("username accepted")
                    self.username = submitted
                    return True
                else: #username denied
                    print("name already taken, try another")
            except ConnectionResetError:
                return self.gracefulClose()

    def awaitRoomEntry(self):
        message = self.receiveMessage()
        while True:
            if (message.messageType == Codes.MSG_ROOM and 
                message.content[0] == Codes.ROOM_JOIN):
                self.rooms.append(message.content[1])
                return
            
    # send a message object to the server
    def sendMessage(self, messageObject):
        messageByte = pickle.dumps(messageObject)
        self.mySocket.send(messageByte)
        print("%s Message Sent: [%s] %s" %
            (Codes.STR_INFO, messageObject.messageType, messageObject.content))
        return

    # await a message from the server
    def receiveMessage(self):
        bytes = self.mySocket.recv(Codes.PACKET_SIZE)
        message = pickle.loads(bytes)
        print("%s Received %s" % (Codes.STR_INFO, message))
        return message

    def handleCommand(self, command):
        print("Command entered,", command)
        commandParts = command.split(" ")
        if (command == "quit"):
            # /quit
            self.sendMessage(Message(self.username,"quit","graceful"))
            print("Closing connection...")
            self.mySocket.close()
            self.mySocket = False
            return
        if (commandParts[0] == "room"):
            # /room join <room name>
            # /room create <room name>
            # /room leave <room name>
            # /room delete <room name>
            if (len(commandParts) == 1):
                print("Usage: \
                    \n\t/room create <room name> \
                    \n\t/room join <room name> \
                    \n\t/room leave <room name> \
                    \n\t/room delete <room name> \
                    \n\t/room current \
                    \n\t/room list")
                return
            if (len(commandParts) == 2):
                if commandParts[1] == "current":
                    print(self.rooms)
                    return
                if commandParts[1] == "list":
                    try:
                        self.sendMessage(
                            Message(
                                self.username,
                                Codes.MSG_ROOM,
                                Codes.ROOM_LIST))
                        print("awaiting room list")
                        return
                    except ConnectionResetError:
                        self.gracefulClose()
                        return
            if (len(commandParts) == 3):
                action = commandParts[1]
                name = commandParts[2]
                try:
                    self.sendMessage(
                        Message(
                            self.username,
                            Codes.MSG_ROOM,
                            (action, name)))
                except ConnectionResetError:
                    self.gracefulClose()
                    return
            return

    def gracefulClose(self):
        print("Leaving server via ConnectionResetError")
        self.mySocket.close()
        self.mySocket = False
        return False