import json
import logging
import socket
import threading
from json import JSONDecodeError

from django.core.serializers.json import DjangoJSONEncoder

from bidpazari.core.runtime.net.constants import TCP_CONFIG, CommandCode
from bidpazari.core.runtime.net.exceptions import InvalidCommand
from bidpazari.core.runtime.net.protocol import (
    CommandContext,
    extract_request_data,
    get_command_by_identifier,
)

logger = logging.getLogger(__name__)


def start_pazar_tcp():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((TCP_CONFIG['HOST'], TCP_CONFIG['PORT']))
    server_sock.listen(TCP_CONFIG['BACKLOG_SIZE'])

    logger.info(
        "Pazar server is listening to connections on port %s", TCP_CONFIG['PORT']
    )

    while True:
        new_socket, client_address = server_sock.accept()
        logger.info(f"New connection: {client_address}")

        thread = threading.Thread(target=handle_commands_tcp, args=(new_socket,))
        thread.start()


def encode_response_tcp(response_dict):
    response_str = json.dumps(
        response_dict, indent=4, sort_keys=True, cls=DjangoJSONEncoder
    )
    return response_str.encode()  # convert str to bytes


def handle_commands_tcp(sock):
    context = CommandContext()
    buffer_size = TCP_CONFIG['BUFFER_SIZE']

    while data_in := sock.recv(buffer_size):
        request = data_in.decode()  # convert bytes to str

        try:
            request_obj = json.loads(request)
            command_identifier, params = extract_request_data(request_obj)
            command_handler = get_command_by_identifier(command_identifier)
            command_result = command_handler(context, **params)
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
            response = encode_response_tcp(command_result)
            sock.send(response)
            sock.close()
            return

        response = encode_response_tcp(command_result)
        sock.send(response)
