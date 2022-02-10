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
            print("Failed to successfully join server. Halting...")
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
                    if text == "/quit":
                        break
                    self.handleCommand(text[1:])
                    continue
                #it is a chat message
                if (len(self.rooms) == 0):
                    print("You are not in any rooms! Use '/room join <room name>' to join one.")
                    continue
                self.sendMessage(Message(self.username, Helper.MSG_TEXT, Helper.NO_SUBTYPE, text, rooms=self.rooms))
            except (ConnectionResetError, KeyboardInterrupt):
                break
        return self.gracefulClose()

    ###########################################################
    # Message Receiving and Handling
    ###########################################################

    # await a message from the server
    def receiveMessage(self):
        bytes = self.mySocket.recv(Helper.PACKET_SIZE)
        message = pickle.loads(bytes)
        # print("%s Received %s" % (Helper.STR_INFO, message))
        return message

    # input a username and submit it to the server. Then await Lobby room entry
    def login(self):
        while self.mySocket:
            submitted = input("Choose an alphanumeric username: ")
            try:
                self.sendMessage(Message(self.username, Helper.MSG_NAME, Helper.NAME_REQUEST, submitted))
                message = self.receiveMessage()
                status = message.subtype
                if (status == Helper.NAME_INVALID): #username not valid
                    print("Username is not valid. Must contain 1-16 alphanumeric characters.")
                elif (status == Helper.NAME_VALID): #username accepted
                    print ("Username accepted.")
                    self.username = submitted
                    break
                else: #username denied
                    print("Username is already taken. Try another.")
            except ConnectionResetError:
                self.gracefulClose()
                return
        message = self.receiveMessage()
        if (message.category == Helper.MSG_ROOM and message.subtype == Helper.ROOM_JOIN):
            print("Joined %s" % message.content)
            self.rooms.append(message.content)
            return True
        return True
            
    # thread function for listening for messages from server
    def listenForMessage(self):
        while self.mySocket:
            try:
                message = self.receiveMessage()
                serverResponse = "%s | %s: " % (message.timeSent, message.sender)
                # we have a plain ol' text chat message from someone
                if (message.category == Helper.MSG_TEXT):
                    timeSent = message.timeSent
                    sender = message.sender
                    rooms = ""
                    for room in message.rooms:
                        rooms = rooms + ("[%s]" % room)
                    textString = message.content
                    print("%s %s %s: %s" % (timeSent, rooms, sender, textString))
                    continue
                elif (message.category == Helper.MSG_WHISPER):
                    if (message.subtype == Helper.SIG_FAIL):
                        print(serverResponse + "Whisper failed to send to " + message.content)
                    else:
                        timeSent = message.timeSent
                        sender = message.sender
                        textString = message.content
                        print("[Whisper] %s %s: %s" % (timeSent, sender, textString))
                else:
                    # we have an update on rooms
                    if (message.category == Helper.MSG_INFO):
                        print(serverResponse + message.content)
                    if (message.category == Helper.MSG_ROOM):
                        #join room successful
                        if (message.subtype == Helper.ROOM_JOIN and message.content != Helper.SIG_FAIL):
                            self.rooms.append(message.content)
                            print(serverResponse + "Successfully joined " + message.content)
                            continue
                        # leave room successful
                        if (message.subtype == Helper.ROOM_LEAVE and message.content != Helper.SIG_FAIL):
                            if (message.content in self.rooms):
                                self.rooms.remove(message.content)
                                print(serverResponse + "Successfully left " + message.content)
                                continue
                        #create room successful
                        if (message.subtype == Helper.ROOM_CREATE and message.content != Helper.SIG_FAIL):
                            if (message.content == Helper.NAME_INVALID):
                                print(serverResponse + "Room name is not valid. Must be alphanumeric between 1-16 characters")
                                continue
                            print(serverResponse + "Successfully created " + message.content)
                            continue
                        elif (message.content == Helper.SIG_FAIL):
                            print(serverResponse + "Failed to perform %s action on room." % message.subtype)
                            continue
            except socket.timeout:
                pass
            except (OSError, ConnectionResetError):
                self.gracefulClose()
                return

    ###########################################################
    # Sending messages to the server
    ###########################################################

    # send a message object to the server
    def sendMessage(self, message):
        messageByte = pickle.dumps(message)
        self.mySocket.send(messageByte)
        # print("%s Message Sent: [%s:%s] %s" % (Helper.STR_INFO, message.category, message.subtype, message.content))
        return

    def handleCommand(self, command):
        components = command.split(" ")
        try:
            if (components[0] == "whisper" or components[0] == "w"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                target = components[1]
                targetLength = len(target)
                textbodyStart = command.find(target) + targetLength
                textbody = command[textbodyStart+1:]
                self.sendMessage(Message(self.username, Helper.MSG_WHISPER, target, textbody))

            if (command == "help"):
                # /help
                print("Available commands: \
                    \n  /quit (Close the client) \
                    \n  /room create <room name> (Create a room) \
                    \n  /room join <room name> (Join a room) \
                    \n  /room leave <room name> (Leave a room) \
                    \n  /room delete <room name> (Request a room be deleted. Must have no clients in it) \
                    \n  /room current (List the rooms that you are currently in) \
                    \n  /info rooms (List all rooms available on the server) \
                    \n  /info users [room name] (List all users on the server, or optionally, a specific room) \
                    \n  /whisper OR /w <username> <message>")
            if (components[0] == "room"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                if (len(components) == 2):
                    if components[1] == "current":
                        print(self.rooms)
                if (len(components) == 3):
                    action = components[1]
                    name = components[2]
                    if (action == "create"):
                        self.sendMessage(Message(self.username, Helper.MSG_ROOM, Helper.ROOM_CREATE, name))
                    if (action == "join"):
                        self.sendMessage(Message(self.username, Helper.MSG_ROOM, Helper.ROOM_JOIN, name))
                    if (action == "leave"):
                        self.sendMessage(Message(self.username, Helper.MSG_ROOM, Helper.ROOM_LEAVE, name))
            if (components[0] == "info"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                if components[1] == "users":
                    if (len(components) == 2):
                        self.sendMessage(Message(self.username, Helper.MSG_INFO, Helper.INFO_USERS, ""))
                        return
                    elif (len(components) == 3):
                        self.sendMessage(Message(self.username, Helper.MSG_INFO, Helper.INFO_USERS, components[2]))
                        return
                if (components[1] == "rooms"):
                    self.sendMessage(Message(self.username, Helper.MSG_INFO, Helper.INFO_ROOMS, ""))
        except ConnectionResetError:
            self.gracefulClose()

    ###########################################################
    # Helper Functions
    ###########################################################

    def gracefulClose(self):
        
        try:
            self.sendMessage(Message(self.username, Helper.MSG_QUIT, Helper.QUIT_GRACEFUL, "thank you"))
            print("Gracefully closing")
        except:
            pass
        try:
            self.mySocket.close()
        except:
            pass
        self.mySocket = False
        return