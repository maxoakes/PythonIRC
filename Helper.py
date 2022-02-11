# static Object for codes
class Helper(object):
    PACKET_SIZE = 4096

    NOT_INIT = ""
    STR_INFO = "[INFO]"
    STR_WARN = "[WARN]"
    STR_ERR = "[ERROR]"
    ROOM_DEFAULT_NAME = "Lobby"

    MSG_NAME = "username"
    MSG_TEXT = "text"
    MSG_ROOM = "room"
    MSG_INFO = "info"
    MSG_SIG = "signal"
    MSG_QUIT = "quit"
    MSG_WHISPER = "whisper"
    ROOM_JOIN = "join"
    ROOM_CREATE = "create"
    ROOM_LEAVE = "leave"
    ROOM_DELETE = "delete"
    INFO_USERS = "users"
    INFO_ROOMS = "rooms"
    QUIT_GRACEFUL = "graceful"
    NO_SUBTYPE = ""

    SIG_SUCCESS = "success"
    SIG_FAIL = "fail"
    SIG_REQUEST = "request"
    SIG_INVALID = "invalid"
    SIG_USED = "used"
