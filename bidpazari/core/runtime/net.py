import json
import logging
import socket
import threading
from decimal import Decimal
from functools import wraps
from json import JSONDecodeError

from bidpazari.core.models import User
from bidpazari.core.runtime.exceptions import CommandFailed
from bidpazari.core.runtime.user import RuntimeUser

logger = logging.getLogger(__name__)


SERVER_HOST = ""
SERVER_PORT = 6671

TCP_BACKLOG = 5
BUFFER_SIZE = 1000

# Registrations handled via @command(...) decorator
COMMANDS = {}


class command:
    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result_dict = func(*args, **kwargs)
                return {"code": 0, "result": {**result_dict}}
            except CommandFailed as e:
                return {"code": 1, "error": {"message": str(e)}}

        # Register command to COMMANDS
        COMMANDS[self.name] = wrapper
        return wrapper


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        runtime_user, *_ = args

        if not runtime_user:
            raise CommandFailed("You must log in to perform this action.")

        return func(*args, **kwargs)

    return wrapper


@command("add_balance")
@login_required
def add_balance(user: RuntimeUser, amount):
    amount = Decimal(amount)
    user.add_balance_transaction(amount)

    return {"current_balance": "{:.2f}".format(user.initial_balance)}


@command("list_items")
@login_required
def list_items(user: RuntimeUser):
    return {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "on_sale": item.on_sale,
            }
            for item in user.list_items()
        ]
    }


@command("view_transaction_history")
@login_required
def view_transaction_history(user: RuntimeUser):
    return {"history": user.transaction_history}


def start_pazar():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((SERVER_HOST, SERVER_PORT))
    sock.listen(TCP_BACKLOG)

    logger.info("Server is listening to connections")

    while True:
        new_socket, client_address = sock.accept()
        logger.info(f"New connection: {client_address}")

        thread = threading.Thread(target=handle_connection, args=(new_socket, client_address))
        thread.start()


def handle_connection(sock, client_address):
    data_in = sock.recv(BUFFER_SIZE)
    runtime_user = None

    while data_in:
        request = data_in.decode()  # convert bytes to str

        request_obj = json.loads(request)
        command_identifier = request_obj["command"]
        params = request_obj["params"]

        if command_identifier == "login":
            username = params.get("username")
            password = params.get("password")

            user = User.objects.get(username=username)  # TODO might not exist

            if user.check_password(password):
                runtime_user = RuntimeUser.from_persistent_user(user)
                runtime_user.connect()

            command_result = {"code": 0, "result": {"id": runtime_user.id}}
        elif command_identifier == "logout":
            sock.close()
            return
        else:
            command_handler = COMMANDS[command_identifier]
            logging.info("Params: %s", params)
            command_result = command_handler(runtime_user, **params)

        response_str = json.dumps(command_result, indent=4, sort_keys=True)
        response = response_str.encode()
        sock.send(response)
        data_in = sock.recv(BUFFER_SIZE)

    sock.close()
