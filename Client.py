import socket
import threading
import pickle
from Message import Message

class Client:
    SIZE = 4096
    username = "undefined"

    def __init__(self, destination, port, username):
        self.username = username

        # create an INET, STREAMing socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((destination, port))
        except ConnectionRefusedError:
            print ("Connection Refused. Closing...")
            return

        print("Connected to "+destination+":"+str(port))
        self.login(sock)

        listening = threading.Thread(
            target = self.listenForServer,
            args=(sock,)
        )
        listening.start()
        print("Listening Thread spawned")
        while True:
            try:
                text = input("!>")
            except KeyboardInterrupt:
                    print("Closing connection...")
                    sock.close()
                    return
            if (text == ""):
                continue
            # is it a command
            if (text[0] == '/'):
                text = text[1:]
                print("Command entered,", text)
                if (text == "quit"):
                    print("Closing connection...")
                    sock.close()
                    return
                else:
                    continue
            
            #it is a chat message
            try:
                self.sendMessage(Message(self.username,"chat",text), sock)
            except ConnectionResetError:
                print("The server has been closed")
                return

    def listenForServer(self, s):
        while True:
            try:
                self.receiveMessage(s)
            except socket.timeout:
                pass
            except OSError:
                return

    def login(self, socket):
        while True:
            submitted = input("Choose a username: ")
            try:
                self.sendMessage(
                    Message(self.username,"username",submitted),
                    socket
                )
                message = self.receiveMessage(socket)
                status = message.content
                self.username = submitted
                if status:
                    return
                else:
                    print("name already taken, try another")
            except ConnectionResetError:
                print("The server has been closed")
                return

    def sendMessage(self, messageObject, socket):
        messageByte = pickle.dumps(messageObject)
        socket.send(messageByte)
        print(
            "[INFO] Message Sent:",
            messageObject.messageType,
            messageObject.content
        )
        return

    def receiveMessage(self, socket):
        bytes = socket.recv(self.SIZE)
        message = pickle.loads(bytes)
        print(
            "[INFO] Message Received:",
            "\n\tSent", message.timeSent,
            "\n\tFrom", message.sender,
            "\n\tType", message.messageType,
            "\n\tContent", message.content
        )
        return message
