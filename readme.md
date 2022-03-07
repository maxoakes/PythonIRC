# Python-based IRC

Complete with channels and private messages. Written in Python 3.10.2. Switch statements were used! They require 3.10.

Added an AutoClient to spam the server every n seconds. Server seems to function with with 5 clients of varying speeds. two of which message every 0.01 seconds. To create an Autoclient, do `py main.py auto <float>`

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
* Clean code even more
* add queues
