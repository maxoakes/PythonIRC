import sys
import threading
from Client import Client
from AutoClient import AutoClient

def main():
    isAutoClient = False
    freq = 1
    if (len(sys.argv) == 3):
        if sys.argv[1] == "auto":
            isAutoClient = True
            freq = sys.argv[2]
    full_addr = input("Server address: ")
    
    #obtain host and port
    destination = 'localhost'
    if (full_addr == ""):
        print("localhost (127.0.0.1) will be used as the destination server")
    else:
        destination = full_addr.split(':')[0]
    port = 7779
    try:
        port = int(full_addr.split(':')[1])
    except IndexError:
        print("default port " + str(port) + " will be used")
    print("Entered address and port:", destination, port)
    if isAutoClient:
        robo = AutoClient(destination, port, "robot", freq)
    else:
        myClient = Client(destination, port, "New User")

if __name__ == '__main__':
    main()