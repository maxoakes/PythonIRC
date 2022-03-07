# Python-based IRC

Complete with channels and private messages. Written in Python 3.10.2. Switch statements were used! They require 3.10.

Added an AutoClient to spam the server every n seconds. Server seems to function with with 5 clients of varying speeds. two of which message every 0.01 seconds. To create an Autoclient, do `py main.py auto <float>`

See rfc.txt for details.

# Basic Criteria
* RFC Document: In progress
  * In reality, it is pretty much done. Just need feedback on what else might be needed/corrected. I added everything I can think of.
* Client can connect to a server: Done
* Client can create a channel: Done
  * `/channel create <room name>` to request to create a channel on the server
* Client can list all channels: Done
  * `/info channels` to list the channels that exist on the server
  * `/channel listening` to list the channels that the client is currently listening to
* Client can join a channel: Done
  * `/channel join <room name>` to request to join a channel that already exists
* Client can leave a channel: Done
  * `/channel leave <room name>` to request to leave a channel that the client is currently in
* Client can list members of a channel: Done
  * `/info users <channel name>` to get a list of users in a channel. Use this command without the channel name to get a list of all users in the server
* Multiple clients can connect to a server: Done
  * Haven't tested this outside of my own computer, but I assume this would work with users outside my network
* Client can send messages to a channel: Done
  * Just enter text and press enter.
* Client can join multiple (selected) channels: Done
  * Client can join a room one at a time, but yes, a client can be in multiple rooms at once. Talking in multiple rooms at once requires a specific action
* Client can send distinct messages to multiple (selected) channels: Done?
  * The "distinct" throws me off. The client can select multiple channels to send a chat message to at the same time, if that is what it means.
* Client can disconnect from a server: Done
  * I think I tested all of the possible ways a client can leave a server
* Server can disconnect from clients: Done
  * The server appears to close gracefully when it needs to
* Server can gracefully handle client crashes: Done
  * I think so
* Client can gracefully handle server crashes: Done
  * I think so
* Extra: Private or Ephemeral Messaging: Done
  * "Private" is questionable. It is more of a direct message that is passed along by the server to one other client
* Extra: Secure messaging: Possible
  * Might just site it as future work in RFC
* Extra: Client can delete channels: Done
  * `/channel delete <channel name>`

# TODO:
* ~~Clean code even more~~
  * Its as clean as I can get short of making a bunch of whitespace
* ~~add queues~~
  * Based on results of stress testing, not sure if this is actually needed...
