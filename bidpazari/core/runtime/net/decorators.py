import asyncio
import json
import threading
from functools import wraps

from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from bidpazari.core.runtime.net.constants import CommandCode
from bidpazari.core.runtime.net.exceptions import CommandFailed


class command:
    def __init__(self, name: str):
        self.name = name

    def __call__(self, func):
        from bidpazari.core.runtime.net.protocol import COMMANDS

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result_dict = await func(*args, **kwargs)
                return {
                    "event": self.name,
                    "timestamp": timezone.now().isoformat(),
                    "code": CommandCode.OK,
                    "result": {**result_dict},
                }
            except CommandFailed as e:
                return {
                    "event": self.name,
                    "timestamp": timezone.now().isoformat(),
                    "code": CommandCode.ERROR,
                    "error": {"message": str(e)},
                }
            except Exception as e:
                return {
                    "event": self.name,
                    "timestamp": timezone.now().isoformat(),
                    "code": CommandCode.FATAL,
                    "error": {"exception": e.__class__.__name__, "message": str(e)},
                }

        # Register command to COMMANDS
        COMMANDS[self.name] = wrapper
        return wrapper


class push_notification:
    def __init__(self, websocket):
        self.websocket = websocket

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def push():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                asyncio.get_event_loop().run_until_complete(
                    self.websocket.send(
                        json.dumps(
                            {
                                'event': 'notification',
                                "timestamp": timezone.now().isoformat(),
                                'code': CommandCode.OK,
                                'result': func(*args, **kwargs),
                            },
                            cls=DjangoJSONEncoder,
                            indent=4,
                            sort_keys=True,
                        )
                    )
                )

            thread = threading.Thread(target=push)
            thread.start()

        return wrapper


def login_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        context, *_ = args

        if not context.runtime_user:
            raise CommandFailed("You must log in to perform this action.")
        return await func(*args, **kwargs)

    return wrapper
