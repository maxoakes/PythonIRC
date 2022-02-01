import traceback
import socket
import threading
import sys
import pickle
from User import User
from Message import Message

SIZE = 4096
activeUsers = []
server_active = True
serverName = "Server"

def main():
    hostname = sys.argv[1]
    port = input("Listening port: ")
    server_active = True
    
    if (port == ""):
        port = 7779
        print("No port specified, using default " + str(port))

    # create an INET, STREAMing socket
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if (hostname == ""):
        hostname = socket.gethostname()

    # bind the socket to a public host, and a well-known port
    serversocket.bind((hostname, int(port)))
    print("Socket Bound:", (hostname, port))

    # become a server socket
    serversocket.listen()
    

    connectionlistening = threading.Thread(
        target=listenForConnections,
        args=(serversocket,)
    )
    connectionlistening.setName("connListener")
    connectionlistening.start()
    
    while server_active:
        message = input("")
        if (message == "quit"):
            server_active = False
            serversocket.close()
            for t in threading.enumerate():
                if (threading.current_thread() != t):
                    t.join()
            print("[INFO] All threads joined. Server program closing gracefully.")
            exit(0)
        if (message == "list"):
            listConnectedClients()

def listenForConnections(serversocket):
    print("[INFO] Now listening for new clients in thread")
    while server_active:
        # accept connections from outside
        print("[INFO] Awaiting connections...")
        try:
            (clientsocket, address) = serversocket.accept()
            print("[INFO] Client connected!", address)
            newUser = registerUser(address[0],address[1], clientsocket)

            listening = threading.Thread(
                target=listenToClient,
                args=(newUser,)
            )
            listening.setName(address[1])
            listening.start()
        except OSError:
            print("[INFO] Client-listening thread function closing.")
            return
    

def listenToClient(user):
    # address = IPv4
    # port = port num
    # username = string
    # id = time in ms
    # connectTime = formatted string
    listenForUsername(user)
    print("[INFO] Now listening for messages:", user.username)
    while server_active:
        try:
            message = receiveMessage(user.socket)
            if message.messageType == "chat":
                broadcast(message, activeUsers)
        except OSError:
            print("[WARN] Connection likely closed:" + user.address[0])
            unregisterUser(user.address[0])
            return

def listenForUsername(user):
    while server_active:
        try:
            print("[INFO] Listening for username from", user.address)
            message = receiveMessage(user.socket)
            submittedName = message.content
            print("[INFO] Submitted name from",user.address, submittedName)
            nameTaken = False
            for u in activeUsers:
                if u.username == submittedName:
                    print("[WARN] Username already in use: "+submittedName)
                    nameTaken = True
                    break
            if nameTaken:
                #name is taken, client needs to retry
                sendMessage(Message(serverName,"signal",False), u.socket)
                pass
            else:
                #name is not taken, set client to that username
                u.username = submittedName
                sendMessage(Message(serverName,"signal",True), u.socket)
                return
        except OSError:
            print("[WARN] Connection likely closed:" + user.address)
            unregisterUser(user.address)
            return


def broadcast(message, users):
    for user in users:
        try:
            sendMessage(message, user.socket)
        except:
            print("[WARN] Broadcast fail!\n"+traceback.format_exc())
            unregisterUser(user.address)

def registerUser(address, port, socket):
    newUser = User(address, port, socket)
    activeUsers.append(newUser)
    print("[INFO] new user added to client list")
    return newUser

def unregisterUser(address):
    for user in activeUsers:
        if user.address == address:
            print(user.username + " unregestered")
            activeUsers.remove(user)
            break
    print("[INFO] unregister done.")

def sendMessage(messageObject, socket):
    messageByte = pickle.dumps(messageObject)
    socket.send(messageByte)
    print(
        "[INFO] Message Sent:",
        messageObject.messageType,
        messageObject.content
    )
    return

def receiveMessage(socket):
    bytes = socket.recv(SIZE)
    message = pickle.loads(bytes)
    print(
        "[INFO] Message Received:",
        "\n\tSent", message.timeSent,
        "\n\tFrom", message.sender,
        "\n\tType", message.messageType,
        "\n\tContent", message.content
    )
    return message

    #server commands
def listConnectedClients():
    for u in activeUsers:
        print(u.username,u.address)

if __name__ == '__main__':
    main()