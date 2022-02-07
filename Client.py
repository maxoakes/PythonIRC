import socket
import threading
import pickle
from Message import Message
from Codes import Codes

class Client:
    SIZE = 4096
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
        listening = threading.Thread(target = self.listenForServer)
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
                print("The server has been closed")
                self.mySocket.close()
                self.mySocket = False
                return
            except KeyboardInterrupt:
                self.handleCommand("quit")
                print("Telling server of closing connection...")
                return

    # thread function for listening for messages from server
    def listenForServer(self):
        while self.mySocket:
            try:
                self.receiveMessage()
            except socket.timeout:
                pass
            except (OSError, ConnectionResetError):
                return

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
                print("The server has been closed")
                return False

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
        bytes = self.mySocket.recv(self.SIZE)
        message = pickle.loads(bytes)
        print("%s Message Received: \
            \n\tSent %s\
            \n\tFrom %s\
            \n\tType %s\
            \n\tContent %s\
            \n\tRooms %s"
            % (Codes.STR_INFO, message.timeSent, message.sender,
                message.messageType, message.content, message.rooms))
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
                    return
            if (len(commandParts) == 3):
                action = commandParts[1]
                name = commandParts[2]
                print("going to %s the room %s" % (action, name))
            return