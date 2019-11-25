import atexit
import json
import logging
import socket
import threading
from decimal import Decimal
from functools import wraps
from json import JSONDecodeError

from django.core.serializers.json import DjangoJSONEncoder

from bidpazari.core.exceptions import BiddingNotAllowed
from bidpazari.core.models import User
from bidpazari.core.runtime.common import runtime_manager
from bidpazari.core.runtime.exceptions import CommandFailed
from bidpazari.core.runtime.user import RuntimeUser

logger = logging.getLogger(__name__)

server_sock = None

SERVER_HOST = ""
SERVER_PORT = 6659

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

    return {"current_balance": user.initial_balance}


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


@command("create_auction")
@login_required
def create_auction(user: RuntimeUser, item_id: int, bidding_strategy_identifier: str, **kwargs):
    # Coerce all floats to decimals
    for key, value in kwargs.items():
        if isinstance(value, float):
            kwargs[key] = Decimal(value)

    auction_id = user.create_auction(
        item_id=item_id, bidding_strategy_identifier=bidding_strategy_identifier, **kwargs
    )
    auction = runtime_manager.active_auctions[auction_id]

    print(auction.to_json())

    return {'auction': {**auction.to_json()}}


@command("start_auction")
@login_required
def start_auction(user: RuntimeUser, auction_id: int):
    auction = runtime_manager.active_auctions[auction_id]

    if user.id == auction.owner.id:
        auction.start()
    else:
        raise CommandFailed("You must be the owner of the auction to perform this action.")

    return {'auction': {**auction.to_json()}}


@command("bid")
@login_required
def bid(user: RuntimeUser, auction_id: int, amount: float):
    auction = runtime_manager.active_auctions[auction_id]
    amount = Decimal(amount)

    try:
        auction.bid(user, amount)
    except BiddingNotAllowed as e:
        raise CommandFailed(f"Bidding not allowed: {e.reason}")

    return {'auction': {**auction.to_json()}}


@command("sell")
@login_required
def sell(user: RuntimeUser, auction_id: int):
    auction = runtime_manager.active_auctions[auction_id]

    if user.id == auction.owner.id:
        auction.sell()
    else:
        raise CommandFailed("You must be the owner of the auction to perform this action.")

    return {'auction': {**auction.to_json()}}


@command("view_auction_report")
@login_required
def view_auction_report(user: RuntimeUser, auction_id: int):
    auction = runtime_manager.active_auctions[auction_id]

    return {'auction': {'report': auction.auction_report}}


@command("view_auction_history")
@login_required
def view_auction_history(user: RuntimeUser, auction_id: int):
    auction = runtime_manager.active_auctions[auction_id]

    return {'auction': {'report': auction.auction_history}}


def start_pazar():
    global server_sock

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((SERVER_HOST, SERVER_PORT))
    server_sock.listen(TCP_BACKLOG)

    logger.info("Pazar server is listening to connections on port %s", SERVER_PORT)

    while True:
        new_socket, client_address = server_sock.accept()
        logger.info(f"New connection: {client_address}")

        thread = threading.Thread(target=handle_commands, args=(new_socket, client_address))
        thread.start()


@atexit.register
def cleanup_pazar():
    server_sock.close()

    logger.info("Terminated Pazar server", SERVER_PORT)


def handle_commands(sock, client_address):
    data_in = sock.recv(BUFFER_SIZE)
    runtime_user = None

    try:
        while data_in:
            request = data_in.decode()  # convert bytes to str

            try:
                request_obj = json.loads(request)
                command_identifier = request_obj["command"]
                params = request_obj["params"]
            except Exception as e:
                command_identifier = None
                command_result = {
                    'code': 3,
                    'error': {'exception': e.__class__.__name__, 'message': str(e)},
                }

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
            elif command_identifier:
                try:
                    command_handler = COMMANDS[command_identifier]
                    command_result = command_handler(runtime_user, **params)
                except Exception as e:
                    command_result = {
                        'code': 2,
                        'error': {'exception': e.__class__.__name__, 'message': str(e)},
                    }

            response_str = json.dumps(
                command_result, indent=4, sort_keys=True, cls=DjangoJSONEncoder
            )
            response = response_str.encode()
            sock.send(response)
            data_in = sock.recv(BUFFER_SIZE)
    finally:
        sock.close()
