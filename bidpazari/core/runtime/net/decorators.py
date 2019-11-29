from functools import wraps

from bidpazari.core.runtime.net.constants import CommandCode
from bidpazari.core.runtime.net.exceptions import CommandFailed


class command:
    def __init__(self, name: str):
        self.name = name

    def __call__(self, func):
        from bidpazari.core.runtime.net.protocol import COMMANDS

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result_dict = func(*args, **kwargs)
                return {
                    "event": self.name,
                    "code": CommandCode.OK,
                    "result": {**result_dict},
                }
            except CommandFailed as e:
                return {
                    "event": self.name,
                    "code": CommandCode.ERROR,
                    "error": {"message": str(e)},
                }
            except Exception as e:
                return {
                    "event": self.name,
                    "code": CommandCode.FATAL,
                    "error": {"exception": e.__class__.__name__, "message": str(e)},
                }

        # Register command to COMMANDS
        COMMANDS[self.name] = wrapper
        return wrapper


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        context, *_ = args

        if not context.runtime_user:
            raise CommandFailed("You must log in to perform this action.")
        return func(*args, **kwargs)

    return wrapper
