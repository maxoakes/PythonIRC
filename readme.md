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
* INFO_USERS, meaning that the client is asking about the list of client's usernames currently in the server. If the content field is not null, the server's response will be the list of client usernames currently in that specified channel. If a channel is not specified, this will always return successful. If a channel is specified and it does not exist, it will return as a failure.
* Verify graceful exits
* Clean code even more
* add queues
