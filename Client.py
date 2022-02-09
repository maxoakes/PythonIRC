import socket
import threading
import pickle
from Message import Message
from Helper import Helper

class Client:
    username = Helper.NOT_INIT
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
                if (len(self.rooms) == 0):
                    print("You are not in any rooms! Use '/room join <room name>' to join one.")
                    continue
                self.sendMessage(
                    Message(self.username,
                        Helper.MSG_TEXT,
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
                # we have a plain ol' text chat message from someone
                if (message.messageType == Helper.MSG_TEXT):
                    timeSent = message.timeSent
                    sender = message.sender
                    rooms = ""
                    for room in message.rooms:
                        rooms = rooms + ("[%s]" % room)
                    textString = message.content
                    print("%s %s %s: %s" % (timeSent, rooms, sender, textString))
                    continue
                else:
                    print("%s Received %s" % (Helper.STR_INFO, message))
                # we have an update on rooms
                if (message.messageType == Helper.MSG_ROOM):
                    #print room list from server
                    if (message.content[0] == Helper.ROOM_LIST and message.content[1]):
                        print(message.content[1])
                        continue
                    #join room successful
                    if (message.content[0] == Helper.ROOM_JOIN and message.content[1]):
                        self.rooms.append(message.content[1])
                        print("Successfully joined %s" % message.content[1])
                        continue
                    if (message.content[0] == Helper.ROOM_LEAVE and message.content[1]):
                        if (message.content[1] in self.rooms):
                            self.rooms.remove(message.content[1])
                            print("Successfully left %s" % message.content[1])
                            continue
                    #create room successful
                    if (message.content[0] == Helper.ROOM_CREATE and message.content[1]):
                        print("Successfully created %s" % message.content[1])
                        continue
                    elif (not message.content[1]):
                        print("Failed to perform action about room")
                        continue
            except socket.timeout:
                pass
            except (OSError, ConnectionResetError):
                return self.gracefulClose()

    # input a username and submit it to the server. Then await Lobby room entry
    def login(self):
        while self.mySocket:
            submitted = input("Choose an alphanumeric username: ")
            try:
                self.sendMessage(
                    Message(self.username, Helper.MSG_NAME, submitted))
                message = self.receiveMessage()
                status = message.content
                if (status == Helper.ACT_INVALID): #username not valid
                    print("Username is not valid. Must contain 1-16 alphanumeric characters.")
                if (status == Helper.ACT_SUCCESS): #username accepted
                    print ("Username accepted.")
                    self.username = submitted
                    break
                else: #username denied
                    print("Username is already taken. Try another.")
            except ConnectionResetError:
                return self.gracefulClose()

        # after a name is accepted by the server, go here, and await word of room entry
        print("Awaiting Lobby room Entry...")
        message = self.receiveMessage()
        if (message.messageType == Helper.MSG_ROOM and message.content[0] == Helper.ROOM_JOIN):
            print("Joined %s" % message.content[1])
            self.rooms.append(message.content[1])
            return True
            
    # send a message object to the server
    def sendMessage(self, messageObject):
        messageByte = pickle.dumps(messageObject)
        self.mySocket.send(messageByte)
        print("%s Message Sent: [%s] %s" % (Helper.STR_INFO, messageObject.messageType, messageObject.content))
        return

    # await a message from the server
    def receiveMessage(self):
        bytes = self.mySocket.recv(Helper.PACKET_SIZE)
        message = pickle.loads(bytes)
        return message

    def handleCommand(self, command):
        components = command.split(" ")
        if (command == "help"):
            # /help
            print("Available commands: \
                  /quit (Close the client) \
                  /room create <room name> (Create a room) \
                  /room join <room name> (Join a room) \
                  /room leave <room name> (Leave a room) \
                  /room delete <room name> (Request a room be deleted. Must have no clients in it) \
                  /room current (List the rooms that you are currently in) \
                  /room list (List all rooms available on the server)")
        if (command == "quit"):
            # /quit
            return self.gracefulClose()
        if (components[0] == "room"):
            # /room join <room name>
            # /room create <room name>
            # /room leave <room name>
            # /room delete <room name>
            if (len(components) == 1):
                print("Refer to the /help command.")
                return
            if (len(components) == 2):
                if components[1] == "current":
                    print(self.rooms)
                    return
                if components[1] == "list":
                    try:
                        self.sendMessage(
                            Message(
                                self.username,
                                Helper.MSG_ROOM,
                                Helper.ROOM_LIST))
                        print("awaiting room list")
                        return
                    except ConnectionResetError:
                        self.gracefulClose()
                        return
            if (len(components) == 3):
                action = components[1]
                name = components[2]
                try:
                    self.sendMessage(
                        Message(
                            self.username,
                            Helper.MSG_ROOM,
                            (action, name)))
                except ConnectionResetError:
                    self.gracefulClose()
                    return
            return

    def gracefulClose(self):
        print("Gracefully closing")
        try:
            self.sendMessage(Message(self.username,"quit","graceful"))
        except:
            print("Server did not recieve client exit notification. It must be down.")
        try:
            self.mySocket.close()
        except:
            print("Client socket failed to close.")
        self.mySocket = False
        return False