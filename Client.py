import socket
import threading
import pickle
from Message import Message
from Helper import Helper

class Client:
    isAlive = True
    username = Helper.NOT_INIT
    mySocket = False
    listeningThread = False
    listeningRooms = []
    shoutRooms = []
    targetRoom = ""
    
    def __init__(self, destination, port, username):
        self.username = username
        self.listeningRooms = []
        self.shoutRooms = []
        self.targetRoom = ""

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
        self.listeningThread = threading.Thread(target = self.listenForMessage)
        self.listeningThread.setName("listening-thread")
        self.listeningThread.start()

        #terminal input loop
        while self.isAlive:
            try:
                text = input("") #await keyboard input
                text = text.strip()
                # it is a blank input
                if (text == ""):
                    continue
                # is it a command
                if (text[0] == '/'):
                    if text == "/quit":
                        self.gracefulClose()
                        break
                    self.handleCommand(text[1:])
                    continue
                #it is a chat message
                if (self.targetRoom == ""):
                    print("You are not targeting any rooms! Use '/room join <room name>' to join one, then /talk <room name> to select an active room")
                    continue
                self.sendMessage(Message(self.username, Helper.MSG_TEXT, Helper.NO_SUBTYPE, Helper.SIG_REQUEST, text, rooms=[self.targetRoom,]))
            except (ConnectionResetError, KeyboardInterrupt) as e:
                self.gracefulClose(e)
        self.listeningThread.join()
        return 

    ###########################################################
    # Message Receiving and Handling
    ###########################################################

    # await a message from the server
    def receiveMessage(self):
        try:
            bytes = self.mySocket.recv(Helper.PACKET_SIZE)
            message = pickle.loads(bytes)
            print("%s Received %s" % (Helper.STR_INFO, message))
            if (isinstance(message, Message)):
                return message
            else:
                print("Message received from server was not of the correct structure")
                self.gracefulClose()
                return False
        except (ConnectionAbortedError, EOFError, OSError) as e:
            self.gracefulClose(e)
            return False

    # input a username and submit it to the server. Then await Lobby room entry
    def login(self):
        #enter username and await word if the name is valid
        while self.isAlive:
            submitted = input("Choose an alphanumeric username: ")
            try:
                self.sendMessage(Message(self.username, Helper.MSG_NAME, Helper.NO_SUBTYPE, Helper.SIG_REQUEST, submitted))
                message = self.receiveMessage()
                if (not message):
                    self.gracefulClose()
                    return False
                status = message.status
                if (status == Helper.SIG_INVALID): #username not valid
                    print("Username is not valid. Must contain 1-16 alphanumeric characters.")
                elif (status == Helper.SIG_SUCCESS): #username accepted
                    print ("Username accepted.")
                    self.username = submitted
                    break
                else: #username denied
                    print("Username is already taken. Try another.")
            except ConnectionAbortedError as e:
                self.gracefulClose(e)
            except Exception as e:
                print("unknown error logging in")
                self.gracefulClose(e)
        #await default room entry
        message = self.receiveMessage()
        if (not message):
            self.gracefulClose()
            return False
        if (message.category == Helper.MSG_ROOM and message.subtype == Helper.ROOM_JOIN):
            print("Joined %s" % message.content)
            self.listeningRooms.append(message.content)
            self.targetRoom = message.content
            return True
        return False
            
    # thread function for listening for messages from server
    def listenForMessage(self):
        while self.isAlive:
            try:
                message = self.receiveMessage()
                if (not message):
                    return
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
                    if (message.status == Helper.SIG_FAIL):
                        print(serverResponse + "Whisper failed to send to " + message.content)
                    else:
                        timeSent = message.timeSent
                        sender = message.sender
                        textString = message.content
                        print("[Whisper] %s %s: %s" % (timeSent, sender, textString))
                elif (message.category == Helper.MSG_INFO):
                    if (message.status == Helper.SIG_FAIL):
                        print("unknown failure getting info")
                    print(serverResponse + message.content)
                elif (message.category == Helper.MSG_ROOM):
                    if (message.subtype == Helper.ROOM_JOIN):
                        if (message.status == Helper.SIG_SUCCESS):
                            self.listeningRooms.append(message.content)
                            print(serverResponse + "Successfully joined " + message.content)
                            continue
                    # leave room successful
                    if (message.subtype == Helper.ROOM_LEAVE):
                        if (message.status == Helper.SIG_SUCCESS):
                            if (message.content in self.listeningRooms):
                                self.listeningRooms.remove(message.content)
                                if (message.content in self.shoutRooms):
                                    self.shoutRooms.remove(message.content)
                                print(serverResponse + "Successfully left " + message.content)
                                continue
                    #create room successful
                    if (message.subtype == Helper.ROOM_CREATE):
                        if (message.status == Helper.SIG_SUCCESS):
                            print(serverResponse + "Successfully created " + message.content)
                            continue
                    # annouce failures
                    if (message.status == Helper.SIG_INVALID):
                        print(serverResponse + "Room name is not valid. Must be alphanumeric between 1-16 characters")
                        continue
                    if (message.status == Helper.SIG_FAIL):
                        print(serverResponse + "Failed to perform %s action on room." % message.subtype)
                        continue
            except socket.timeout:
                pass
            except ConnectionResetError as e:
                self.gracefulClose(e)
            except OSError:
                print("General OSError in listenForMessage")

    ###########################################################
    # Sending messages to the server
    ###########################################################

    # send a message object to the server
    def sendMessage(self, message):
        try:
            messageByte = pickle.dumps(message)
            self.mySocket.send(messageByte)
            # print("%s Message Sent: [%s:%s] %s" % (Helper.STR_INFO, message.category, message.subtype, message.content))
        except (ConnectionResetError, OSError) as e:
            print("Unable to send to server")
            if message.category == Helper.MSG_QUIT:
                return
            self.gracefulClose(e)

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
                self.sendMessage(Message(self.username, Helper.MSG_WHISPER, target, Helper.SIG_REQUEST, textbody))
            if (command == "help"):
                # /help
                print("Available commands: \
                    \n  /quit (Close the client) \
                    \n  /room create <room name> (Create a room) \
                    \n  /room join <room name> (Join a room) \
                    \n  /room leave <room name> (Leave a room) \
                    \n  /room delete <room name> (Request a room be deleted. Must have no clients in it) \
                    \n  /room listening (List the rooms that you are currently in) \
                    \n  /shoutset <room 1> <room 2> ... <room n> (Declare the rooms to shout into) \
                    \n  /shout <message> (Send a message to all of your shout rooms) \
                    \n  /info rooms (List all rooms available on the server) \
                    \n  /info users [room name] (List all users on the server, or optionally, a specific room) \
                    \n  /whisper OR /w <username> <message>")
            if (components[0] == "room"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                if (len(components) == 2):
                    if components[1] == "listening":
                        print(self.listeningRooms)
                    if components[1] == "shouting":
                        print(self.shoutRooms)
                if (len(components) == 3):
                    action = components[1]
                    name = components[2]
                    if (action == "create"):
                        self.sendMessage(Message(self.username, Helper.MSG_ROOM, Helper.ROOM_CREATE, Helper.SIG_REQUEST, name))
                    if (action == "join"):
                        self.sendMessage(Message(self.username, Helper.MSG_ROOM, Helper.ROOM_JOIN, Helper.SIG_REQUEST, name))
                    if (action == "leave"):
                        self.sendMessage(Message(self.username, Helper.MSG_ROOM, Helper.ROOM_LEAVE, Helper.SIG_REQUEST, name))
            if (components[0] == "info"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                if components[1] == "users":
                    if (len(components) == 2):
                        self.sendMessage(Message(self.username, Helper.MSG_INFO, Helper.INFO_USERS, Helper.SIG_REQUEST, ""))
                        return
                    elif (len(components) == 3):
                        self.sendMessage(Message(self.username, Helper.MSG_INFO, Helper.INFO_USERS, Helper.SIG_REQUEST, components[2]))
                        return
                if (components[1] == "rooms"):
                    self.sendMessage(Message(self.username, Helper.MSG_INFO, Helper.INFO_ROOMS, Helper.SIG_REQUEST, ""))
            if (components[0] == "shoutset"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                for room in components[1:]:
                    if room in self.listeningRooms:
                        if room not in self.shoutRooms:
                            self.shoutRooms.append(room)
                print("Shout rooms set to: %s" % ", ".join(self.shoutRooms))
            if (components[0] == "shout"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                textbody = command[len(components[0])+1:]
                self.sendMessage(Message(self.username, Helper.MSG_TEXT, Helper.NO_SUBTYPE, Helper.SIG_REQUEST, textbody, rooms=self.shoutRooms))
            if (components[0] == "talk"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                if components[1] in self.listeningRooms:
                    self.targetRoom = components[1]
                    print("Talking room set to %s" % self.targetRoom)
                
        except ConnectionResetError as e:
            self.gracefulClose(e)

    ###########################################################
    # Helper Functions
    ###########################################################

    def gracefulClose(self, errorType=None):
        mutex = threading.Lock()
        mutex.acquire()
        if (not self.isAlive):
            mutex.release()
            return # if this function has already been run, just return
        self.isAlive = False
        try:
            print("Attempting to inform server of shutdown (With error %s)" % errorType)
            self.sendMessage(Message(self.username, Helper.MSG_QUIT, Helper.QUIT_GRACEFUL, Helper.SIG_REQUEST, "thank you"))
        except:
            pass
        print("Gracefully closing client via %s." % threading.current_thread().getName())
        try:
            self.mySocket.close()
        except:
            pass
        mutex.release()
        if (threading.current_thread() != threading.main_thread()):
            print("Press ENTER to close.")