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
                self.sendMessage(Message(self.username, Helper.MSG_TEXT, text, rooms=self.rooms))
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
        return message

    # input a username and submit it to the server. Then await Lobby room entry
    def login(self):
        while self.mySocket:
            submitted = input("Choose an alphanumeric username: ")
            try:
                self.sendMessage(Message(self.username, Helper.MSG_NAME, submitted))
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
                self.gracefulClose()
                return
        message = self.receiveMessage()
        if (message.category == Helper.MSG_ROOM and message.content[0] == Helper.ROOM_JOIN):
            print("Joined %s" % message.content[1])
            self.rooms.append(message.content[1])
            return True
        return True
            
    # thread function for listening for messages from server
    def listenForMessage(self):
        while self.mySocket:
            try:
                message = self.receiveMessage()
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
                else:
                    print("%s Received %s" % (Helper.STR_INFO, message))
                #if we get here, the message that was recieved was something from the server
                printStatement = "%s | %s: " % (message.timeSent, message.sender)
                # we have an update on rooms
                if (message.category == Helper.MSG_ROOM):
                    #print room list from server
                    if (message.content[0] == Helper.ROOM_LIST and message.content[1]):
                        print(printStatement + message.content[1])
                        continue
                    #join room successful
                    if (message.content[0] == Helper.ROOM_JOIN and message.content[1]):
                        self.rooms.append(message.content[1])
                        print(printStatement + "Successfully joined " + message.content[1])
                        continue
                    if (message.content[0] == Helper.ROOM_LEAVE and message.content[1]):
                        if (message.content[1] in self.rooms):
                            self.rooms.remove(message.content[1])
                            print(printStatement + "Successfully left " + message.content[1])
                            continue
                    #create room successful
                    if (message.content[0] == Helper.ROOM_CREATE and message.content[1]):
                        print(printStatement + "Successfully created " + message.content[1])
                        continue
                    elif (not message.content[1]):
                        print(printStatement + "Failed to perform action about room.")
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
        print("%s Message Sent: [%s] %s" % (Helper.STR_INFO, message.category, message.content))
        return

    def handleCommand(self, command):
        components = command.split(" ")
        try:
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
            if (components[0] == "room"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                if (len(components) == 2):
                    if components[1] == "current":
                        print(self.rooms)
                        return
                    if components[1] == "list":
                        self.sendMessage(Message(self.username,Helper.MSG_ROOM,Helper.ROOM_LIST))
                        print("awaiting room list")
                        return
                if (len(components) == 3):
                    action = components[1]
                    name = components[2]
                    self.sendMessage(Message(self.username,Helper.MSG_ROOM,(action, name)))
        except ConnectionResetError:
            self.gracefulClose()

    ###########################################################
    # Helper Functions
    ###########################################################

    def gracefulClose(self):
        
        try:
            self.sendMessage(Message(self.username,"quit","graceful"))
            print("Gracefully closing")
        except:
            pass
        try:
            self.mySocket.close()
        except:
            pass
        self.mySocket = False
        return