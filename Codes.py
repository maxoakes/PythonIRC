# static Object for codes
class Codes(object):
    PACKET_SIZE = 4096
    NOT_INIT = "__undefined__"
    STR_INFO = "[INFO]"
    STR_WARN = "[WARN]"
    STR_ERR = "[ERROR]"

    MSG_NAME = "username"
    MSG_TEXT = "text"
    MSG_ROOM = "room"
    MSG_SIG = "signal"
    MSG_QUIT = "quit"

    ROOM_DEFAULT_NAME = "Lobby"
    ROOM_JOIN = "join"
    ROOM_CREATE = "create"
    ROOM_LEAVE = "leave"
    ROOM_DELETE = "delete"
    ROOM_LIST = "list"

    ACT_SUCCESS = True
    ACT_FAIL = False