# static Object for codes
class Codes(object):
    PACKET_SIZE = 4096

    NOT_INIT = ""
    STR_INFO = "[INFO]"
    STR_WARN = "[WARN]"
    STR_ERR = "[ERROR]"
    CHANNEL_DEFAULT_NAME = "Lobby"

    MSG_NAME = "username"
    MSG_TEXT = "text"
    MSG_CHANNEL = "channel"
    MSG_INFO = "info"
    MSG_SIG = "signal"
    MSG_QUIT = "quit"
    MSG_WHISPER = "whisper"
    CHANNEL_JOIN = "join"
    CHANNEL_CREATE = "create"
    CHANNEL_LEAVE = "leave"
    CHANNEL_DELETE = "delete"
    INFO_USERS = "users"
    INFO_CHANNELS = "channels"
    QUIT_GRACEFUL = "graceful"
    NO_SUBTYPE = ""

    SIG_SUCCESS = "success"
    SIG_FAIL = "fail"
    SIG_REQUEST = "request"
    SIG_INVALID = "invalid"
    SIG_USED = "used"
