from enum import IntEnum

SERVER_HOST = ""
SERVER_PORT = 6659
TCP_BACKLOG = 5
BUFFER_SIZE = 1000


class CommandCode(IntEnum):
    OK = 0
    ERROR = 1
    FATAL = 2
