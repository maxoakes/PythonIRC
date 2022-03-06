import socket
import threading
import pickle
from Message import Message
from Codes import Codes as OP

class Client:
    isAlive = True # boolean
    username = "" # string
    mySocket = "" # socket
    listeningThread = "" # thread
    listeningChannels = [] # list of strings
    shoutChannels = [] # list of strings
    targetChannel = "" # string
    
    def __init__(self, destination, port, username):
        self.username = username
        self.listeningChannels = []
        self.shoutChannels = []
        self.targetChannel = ""
        self.isAlive = True

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

    # await a message from the server
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

    # input a username and submit it to the server. Then await Lobby channel entry
    def login(self):
        #enter username and await word if the name is valid
        while self.isAlive:
            submitted = input("Choose an alphanumeric username: ")
            try:
                self.sendMessage(Message(self.username, OP.MSG_NAME, OP.NO_SUBTYPE, OP.SIG_REQUEST, submitted))
                message = self.receiveMessage()
                if (not message):
                    self.gracefulClose()
                    return False
                status = message.status
                if (status == OP.SIG_INVALID): #username not valid
                    print("Username is not valid. Must contain 1-16 alphanumeric characters.")
                elif (status == OP.SIG_SUCCESS): #username accepted
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
        #await default channel entry
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
            
    # thread function for listening for messages from server
    def listenForMessage(self):
        while self.isAlive:
            try:
                message = self.receiveMessage()
                if (not message):
                    return
                # prefix string shown to user in the case of messages from the server/control messages
                # not used when it is a text message from another user
                serverResponse = "%s | %s: " % (message.timeSent, message.sender)
                # we have a plain ol' text chat message from someone
                if (message.category == OP.MSG_TEXT):
                    timeSent = message.timeSent
                    sender = message.sender
                    channels = ""
                    for channel in message.channels:
                        channels = channels + ("[%s]" % channel)
                    textString = message.content
                    print("%s %s %s: %s" % (timeSent, channels, sender, textString))
                    continue
                elif (message.category == OP.MSG_WHISPER):
                    if (message.status == OP.SIG_FAIL):
                        print(serverResponse + "Whisper failed to send to " + message.content)
                    else:
                        timeSent = message.timeSent
                        sender = message.sender
                        textString = message.content
                        print("[Whisper] %s %s: %s" % (timeSent, sender, textString))
                elif (message.category == OP.MSG_INFO):
                    print(serverResponse + message.content)
                elif (message.category == OP.MSG_CHANNEL):
                    if (message.subtype == OP.CHANNEL_JOIN):
                        if (message.status == OP.SIG_SUCCESS):
                            self.listeningChannels.append(message.content)
                            print(serverResponse + "Successfully joined " + message.content)
                            continue
                    # leave channel successful
                    if (message.subtype == OP.CHANNEL_LEAVE):
                        if (message.status == OP.SIG_SUCCESS):
                            if (message.content in self.listeningChannels):
                                self.listeningChannels.remove(message.content)
                                if (message.content in self.shoutChannels):
                                    self.shoutChannels.remove(message.content)
                                print(serverResponse + "Successfully left " + message.content)
                                continue
                    #create channel successful
                    if (message.subtype == OP.CHANNEL_CREATE):
                        if (message.status == OP.SIG_SUCCESS):
                            print(serverResponse + "Successfully created " + message.content)
                            continue
                    # annouce failures
                    if (message.status == OP.SIG_INVALID):
                        print(serverResponse + "Channel name is not valid. Must be alphanumeric between 1-16 characters")
                        continue
                    if (message.status == OP.SIG_FAIL):
                        print(serverResponse + "Failed to perform %s action on channel." % message.subtype)
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
            # print("%s Message Sent: [%s:%s] %s" % (OP.STR_INFO, message.category, message.subtype, message.content))
        except (ConnectionResetError, OSError) as e:
            print("Unable to send to server")
            if message.category == OP.MSG_QUIT:
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
                self.sendMessage(Message(self.username, OP.MSG_WHISPER, target, OP.SIG_REQUEST, textbody))
            if (command == "help" or command == ""):
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
            if (components[0] == "channel" or components[0] == "c"):
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
            if (components[0] == "info" or components[0] == "i"):
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
            if (components[0] == "shoutset" or components[0] == "ss"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                for channel in components[1:]:
                    if channel in self.listeningChannels:
                        if channel not in self.shoutChannels:
                            self.shoutChannels.append(channel)
                print("Shout channels set to: %s" % ", ".join(self.shoutChannels))
            if (components[0] == "shout" or components[0] == "s"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                textbody = command[len(components[0])+1:]
                self.sendMessage(Message(self.username, OP.MSG_TEXT, OP.NO_SUBTYPE, OP.SIG_REQUEST, textbody, channels=self.shoutChannels))
            if (components[0] == "talk" or components[0] == "t"):
                if (len(components) == 1):
                    print("Refer to the /help command.")
                    return
                if components[1] in self.listeningChannels:
                    self.targetChannel = components[1]
                    print("Talking channel set to %s" % self.targetChannel)
                
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