import socket
import threading
import pickle
from Message import Message
from Codes import Codes as OP
import time
import random

# An automatic client used to test high traffic on the server
class AutoClient:
    isAlive = True # boolean
    username = "" # string
    mySocket = "" # socket
    listeningThread = "" # thread
    listeningChannels = [] # list of strings
    shoutChannels = [] # list of strings
    targetChannel = "" # string
    talkingFreq = 1.0
    
    def __init__(self, destination, port, username, freq):
        self.username = username
        self.listeningChannels = []
        self.shoutChannels = []
        self.targetChannel = ""
        self.isAlive = True
        self.talkingFreq = float(freq)

        # Create an INET, STREAMing socket
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

        # Spawn listening thread
        self.listeningThread = threading.Thread(target = self.listenForMessage)
        self.listeningThread.setName("listening-thread")
        self.listeningThread.start()

        # Terminal input loop
        while self.isAlive:
            try:
                r = random.random()
                time.sleep(self.talkingFreq)
                text = ""
                if 0 <= r <= 0.2:
                    randomAction = random.choice(["create","delete","join","leave"])
                    text = "/c " + randomAction + " " + self.generateWord(1)
                elif 0.2 <= r <= 0.3:
                    text = "/t " + random.choice(self.listeningChannels)
                else:
                    text = self.generateWord(3)
                # Is it a command
                if (text[0] == '/'):
                    if text == "/quit":
                        self.gracefulClose()
                        break
                    self.handleCommand(text[1:])
                    continue
                # It is a chat message
                if (self.targetChannel == ""):
                    print("You are not targeting any channels! Use '/channel join <channel name>' to join one, then /talk <channel name> to select an active channel")
                    continue
                self.sendMessage(Message(self.username, OP.MSG_TEXT, OP.NO_SUBTYPE, OP.SIG_REQUEST, text, channels=[self.targetChannel,]))
            except (ConnectionResetError, KeyboardInterrupt) as e:
                self.gracefulClose(e)
        self.listeningThread.join()
        return 

    ###########################################################
    # Message Receiving and Handling
    ###########################################################

    # Await a message from the server
    def receiveMessage(self):
        try:
            bytes = self.mySocket.recv(OP.PACKET_SIZE)
            message = pickle.loads(bytes)
            # print("%s Received %s" % (OP.STR_INFO, message))
            if (isinstance(message, Message)):
                return message
            else:
                print("Message received from server was not of the correct structure")
                self.gracefulClose()
                return False
        except (ConnectionAbortedError, EOFError, OSError) as e:
            self.gracefulClose(e)
            return False

    # Input a username and submit it to the server. Then await Lobby channel entry
    def login(self):
        # Enter username and await word if the name is valid
        while self.isAlive:
            submitted = self.generateWord(10)
            time.sleep(1)
            try:
                self.sendMessage(Message(self.username, OP.MSG_NAME, OP.NO_SUBTYPE, OP.SIG_REQUEST, submitted))
                message = self.receiveMessage()
                if (not message):
                    self.gracefulClose()
                    return False
                status = message.status
                if (status == OP.SIG_INVALID): # Username not valid
                    print("Username is not valid. Must contain 1-16 alphanumeric characters.")
                elif (status == OP.SIG_SUCCESS): # Username accepted
                    print ("Username accepted.")
                    self.username = submitted
                    break
                else: # Username denied
                    print("Username is already taken. Try another.")
            except ConnectionAbortedError as e:
                self.gracefulClose(e)
            except Exception as e:
                print("unknown error logging in")
                self.gracefulClose(e)
        # Await default channel entry
        message = self.receiveMessage()
        if (not message):
            self.gracefulClose()
            return False
        if (message.category == OP.MSG_CHANNEL and message.subtype == OP.CHANNEL_JOIN):
            print("Joined %s" % message.content)
            self.listeningChannels.append(message.content)
            self.targetChannel = message.content
            return True
        return False
            
    # Thread function for listening for messages from server
    def listenForMessage(self):
        while self.isAlive:
            try:
                message = self.receiveMessage()
                if (not message):
                    return
                # Prefix string shown to user in the case of messages from the server/control messages
                # Not used when it is a text message from another user
                serverResponse = "%s | %s: " % (message.timeSent, message.sender)
                match message.category:
                    # We have a plain ol' text chat message from someone
                    case OP.MSG_TEXT:
                        timeSent = message.timeSent
                        sender = message.sender
                        channels = ""
                        for channel in message.channels:
                            channels = channels + ("[%s]" % channel)
                        textString = message.content
                        print("%s* %s %s %s: %s" % (self.username, timeSent, channels, sender, textString))
                        continue
                    # Message is a whisper from someone (or an attempted whisper from me)
                    case OP.MSG_WHISPER:
                        if (message.status == OP.SIG_FAIL):
                            print(serverResponse + "Whisper failed to send to " + message.content)
                        else:
                            timeSent = message.timeSent
                            sender = message.sender
                            textString = message.content
                            print("[Whisper] %s %s: %s" % (timeSent, sender, textString))
                    # Message is info from the server about user lists
                    case OP.MSG_INFO:
                        print(serverResponse + message.content)
                    # Message is a response about a channel action.
                    case OP.MSG_CHANNEL:
                        match message.subtype:
                            # Join channel successful
                            case OP.CHANNEL_JOIN:
                                if (message.status == OP.SIG_SUCCESS):
                                    self.listeningChannels.append(message.content)
                                    print(serverResponse + "Successfully joined " + message.content)
                                    continue
                            # Leave channel successful
                            case OP.CHANNEL_LEAVE:
                                if (message.status == OP.SIG_SUCCESS):
                                    if (message.content in self.listeningChannels):
                                        self.listeningChannels.remove(message.content)
                                        if (message.content in self.shoutChannels):
                                            self.shoutChannels.remove(message.content)
                                        print(serverResponse + "Successfully left " + message.content)
                                        if self.targetChannel == message.content:
                                            print("Left talking channel. Use '/talk' <channel name> to choose a new default channel")
                                            self.targetChannel = ""
                                        continue
                            # Create channel successful
                            case OP.CHANNEL_CREATE:
                                if (message.status == OP.SIG_SUCCESS):
                                    print(serverResponse + "Successfully created " + message.content)
                                    continue
                            # Deletion of channel successful
                            case OP.CHANNEL_DELETE:
                                if (message.status == OP.SIG_SUCCESS):
                                    print(serverResponse + "Successfully deleted " + message.content)
                                    continue
                        # Annouce failures
                        if (message.status == OP.SIG_INVALID):
                            print(serverResponse + "Channel name is not valid. Must be alphanumeric between 1-16 characters")
                            continue
                        if (message.status == OP.SIG_FAIL):
                            print(serverResponse + "Failed to perform %s action on channel." % message.subtype)
                            continue
                    case _:
                        print ("Unknown message received from server")
            except socket.timeout:
                pass
            except ConnectionResetError as e:
                self.gracefulClose(e)
            except OSError:
                print("General OSError in listenForMessage")

    ###########################################################
    # Sending messages to the server
    ###########################################################

    # Send a message object to the server
    def sendMessage(self, message):
        try:
            messageByte = pickle.dumps(message)
            self.mySocket.send(messageByte)
            # print("%s Message Sent: [%s:%s] %s" % (OP.STR_INFO, message.category, message.subtype, message.content))
        except (ConnectionResetError, OSError) as e:
            print("Unable to send to server")
            # In the case that the loose connection to the server,
            # and the automatic graceful close takes place; we won't need to gracefully close again
            if message.category == OP.MSG_QUIT:
                return
            self.gracefulClose(e)

    # Parse the command given from the user's keyboard input. The / at the front is already removed.
    def handleCommand(self, command):
        components = command.split(" ")
        try:
            match components[0]:
                case "help" | "":
                    # /help
                    print("Available commands: \
                        \n  /quit (Close the client) \
                        \n  /channel create <channel name> (Create a channel) \
                        \n  /channel join <channel name> (Join a channel) \
                        \n  /channel leave <channel name> (Leave a channel) \
                        \n  /channel delete <channel name> (Request a channel be deleted. Must have no clients in it) \
                        \n  /channel listening (List the channels that you are currently in) \
                        \n  /shoutset <channel 1> <channel 2> ... <channel n> (Declare the channels to shout into) \
                        \n  /shout <message> (Send a message to all of your shout channels) \
                        \n  /info channels (List all channels available on the server) \
                        \n  /info users [channel name] (List all users on the server, or optionally, a specific channel) \
                        \n  /whisper OR <username> <message> \
                        \n aliases are whisper=w, channel=c, shoutset=ss, shout=s, talk=t, info=i")
                case "whisper" | "w":
                    if (len(components) == 1):
                        print("Refer to the /help command.")
                        return
                    target = components[1]
                    targetLength = len(target)
                    textbodyStart = command.find(target) + targetLength
                    textbody = command[textbodyStart+1:]
                    self.sendMessage(Message(self.username, OP.MSG_WHISPER, target, OP.SIG_REQUEST, textbody))
                case "channel" | "c":
                    if (len(components) == 1):
                        print("Refer to the /help command.")
                        return
                    if (len(components) == 2):
                        if components[1] == "listening":
                            print(self.listeningChannels)
                        if components[1] == "shouting":
                            print(self.shoutChannels)
                    if (len(components) == 3):
                        action = components[1]
                        name = components[2]
                        if (action == "create"):
                            self.sendMessage(Message(self.username, OP.MSG_CHANNEL, OP.CHANNEL_CREATE, OP.SIG_REQUEST, name))
                        if (action == "join"):
                            self.sendMessage(Message(self.username, OP.MSG_CHANNEL, OP.CHANNEL_JOIN, OP.SIG_REQUEST, name))
                        if (action == "leave"):
                            self.sendMessage(Message(self.username, OP.MSG_CHANNEL, OP.CHANNEL_LEAVE, OP.SIG_REQUEST, name))
                        if (action == "delete"):
                            self.sendMessage(Message(self.username, OP.MSG_CHANNEL, OP.CHANNEL_DELETE, OP.SIG_REQUEST, name))
                case "info" |"i":
                    if (len(components) == 1):
                        print("Refer to the /help command.")
                        return
                    if components[1] == "users":
                        if (len(components) == 2):
                            self.sendMessage(Message(self.username, OP.MSG_INFO, OP.INFO_USERS, OP.SIG_REQUEST, ""))
                            return
                        elif (len(components) == 3):
                            self.sendMessage(Message(self.username, OP.MSG_INFO, OP.INFO_USERS, OP.SIG_REQUEST, components[2]))
                            return
                    if (components[1] == "channels"):
                        self.sendMessage(Message(self.username, OP.MSG_INFO, OP.INFO_CHANNELS, OP.SIG_REQUEST, ""))
                case "shoutset" | "ss":
                    if (len(components) == 1):
                        print("Refer to the /help command.")
                        return
                    for channel in components[1:]:
                        if channel in self.listeningChannels:
                            if channel not in self.shoutChannels:
                                self.shoutChannels.append(channel)
                    print("Shout channels set to: %s" % ", ".join(self.shoutChannels))
                case "shout" | "s":
                    if (len(components) == 1):
                        print("Refer to the /help command.")
                        return
                    textbody = command[len(components[0])+1:]
                    self.sendMessage(Message(self.username, OP.MSG_TEXT, OP.NO_SUBTYPE, OP.SIG_REQUEST, textbody, channels=self.shoutChannels))
                case "talk" | "t":
                    if (len(components) == 1):
                        print("Refer to the /help command.")
                        return
                    if components[1] in self.listeningChannels:
                        self.targetChannel = components[1]
                        print("Talking channel set to %s" % self.targetChannel)
                case _:
                    print("Unknown command. Refer to /help.")
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
            self.sendMessage(Message(self.username, OP.MSG_QUIT, OP.QUIT_GRACEFUL, OP.SIG_REQUEST, "thank you"))
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
    
    def generateWord(self, length):
       return ''.join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for x in range(length))
