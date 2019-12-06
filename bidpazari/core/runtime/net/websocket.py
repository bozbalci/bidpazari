import asyncio
import json
import logging
import traceback
from json import JSONDecodeError

import websockets
from django.core.serializers.json import DjangoJSONEncoder

from bidpazari.core.runtime.net.constants import WS_CONFIG, CommandCode
from bidpazari.core.runtime.net.exceptions import InvalidCommand
from bidpazari.core.runtime.net.protocol import (
    CommandContext,
    extract_request_data,
    get_command_by_identifier,
)

logger = logging.getLogger(__name__)


def start_pazar_ws():
    start_ws = websockets.serve(
        handle_commands_ws, WS_CONFIG['HOST'], WS_CONFIG['PORT']
    )
    asyncio.get_event_loop().run_until_complete(start_ws)
    asyncio.get_event_loop().run_forever()


def encode_response_ws(response_dict):
    return json.dumps(response_dict, indent=4, sort_keys=True, cls=DjangoJSONEncoder)


async def handle_commands_ws(websocket, path):
    context = CommandContext(websocket=websocket)
    command_result = {}

    while request := await websocket.recv():
        try:
            request_obj = json.loads(request)
            command_identifier, params = extract_request_data(request_obj)
            command_handler = get_command_by_identifier(command_identifier)
            command_result = await command_handler(context, **params)
        except (JSONDecodeError, InvalidCommand) as e:
            command_result = {
                'code': CommandCode.FATAL,
                'error': {'exception': e.__class__.__name__, 'message': str(e)},
            }
        except Exception as e:
            logger.error(f'Unexpected exception: {e}')
            command_result = {
                'code': CommandCode.FATAL,
                'error': {'exception': e.__class__.__name__, 'message': str(e)},
            }
            traceback.print_tb(e.__traceback__)
        finally:
            response = encode_response_ws(command_result)
            await websocket.send(response)
