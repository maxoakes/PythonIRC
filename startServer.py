from Server import Server
import sys

def main():
    hostname = ""
    port = ""
    if (len(sys.argv) == 2):
        hostname = sys.argv[1]
    else:
        hostname = input("Server address: ")
    
    if (len(sys.argv) == 3):
        port = sys.argv[2]
    else:
        port = input("Server port: ")
    print("spawning server with parameters %s:%s" % (hostname, port))
    myServer = Server(hostname, port, "Server")

if __name__ == '__main__':
    main()