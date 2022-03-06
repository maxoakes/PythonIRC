# Python-based IRC

Complete with channels and private messages.

See rfc.txt for details.

# Basic Criteria
* RFC Document: In progress
* Client can connect to a server: Done
* Client can create a channel: Done
* Client can list all channels: Done
* Client can join a channel: Done
* Client can leave a channel: Done
* Client can list members of a channel: Done
* Multiple clients can connect to a server: Done
* Client can send messages to a channel: Done
* Client can join multiple (selected) channels: Done
* Client can send distinct messages to multiple (selected) channels: Done?
* Client can disconnect from a server: Done
* Server can disconnect from clients: Done
* Server can gracefully handle client crashes: Done
* Client can gracefully handle server crashes: Done
* Extra: Private or Ephemeral Messaging: Done
* Extra: Secure messaging: Possible, might just site it as future work in RFC

# TODO:
* Graceful exitting of the client application process is done via the "/quit" command. When this command is inputted, the client will send a MSG_QUIT message to the server and subsequently close the socket, and close all threads of the application. Using a keyboard shortcut such as Control-C will also perform the actions of the "/quit" command. THE CLIENT SHOULD AWAIT EOF FROM SERVER BEFORE CLOSING THE SOCKET. will need to revise 3.4.5
* Verify graceful exits
* Clean code even more
* add queues
