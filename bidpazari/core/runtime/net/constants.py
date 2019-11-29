from enum import IntEnum


TCP_CONFIG = {
    'HOST': '',
    'PORT': 6659,
    'BACKLOG_SIZE': 5,
    'BUFFER_SIZE': 1000,
}

WS_CONFIG = {
    'HOST': '0.0.0.0',
    'PORT': 8765,
}


class CommandCode(IntEnum):
    OK = 0
    ERROR = 1
    FATAL = 2
