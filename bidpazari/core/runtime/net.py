import atexit
import json
import logging
import socket
import threading
from decimal import Decimal
from functools import wraps
from json import JSONDecodeError
from typing import Union

from django.core.serializers.json import DjangoJSONEncoder

from bidpazari.core.exceptions import (
    BiddingNotAllowed,
    InvalidPassword,
    UserVerificationError,
)
from bidpazari.core.models import User
from bidpazari.core.runtime.common import runtime_manager
from bidpazari.core.runtime.constants import (
    SERVER_HOST,
    SERVER_PORT,
    TCP_BACKLOG,
    BUFFER_SIZE,
    CommandCode,
)
from bidpazari.core.runtime.exceptions import (
    CommandFailed,
    InvalidCommand,
    AuctionDoesNotExist,
)
from bidpazari.core.runtime.user import RuntimeUser

logger = logging.getLogger(__name__)

server_sock = None

# Registrations handled via @command(...) decorator
COMMANDS = {}


class CommandContext:
    """
    Container class for everything required to run a command. Passed as the first parameter
    of every command function.
    """

    def __init__(self, runtime_user: RuntimeUser = None):
        self.runtime_user = runtime_user


class command:
    def __init__(self, name: str):
        self.name = name

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result_dict = func(*args, **kwargs)
                return {"code": CommandCode.OK, "result": {**result_dict}}
            except CommandFailed as e:
                return {"code": CommandCode.ERROR, "error": {"message": str(e)}}
            except Exception as e:
                return {
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


@command("create_user")
def create_user(
    context: CommandContext,
    username: str,
    password: str,
    email: str,
    first_name: str,
    last_name: str,
):
    """
    Creates an user and immediately logs in.
    """
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    runtime_user = RuntimeUser.from_persistent_user(user)
    context.runtime_user = runtime_user
    return {'user': {'id': user.id}}


@command("login")
def login(context: CommandContext, username: str, password: str):
    if context.runtime_user:
        raise CommandFailed("You are already logged in!")

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise CommandFailed("Incorrect username or password.")

    if user.check_password(password):
        runtime_user = RuntimeUser.from_persistent_user(user)
    else:
        raise CommandFailed("Incorrect username or password.")

    runtime_user.connect()
    context.runtime_user = runtime_user
    return {"user": {"id": runtime_user.id}}


@command("change_password")
@login_required
def change_password(context: CommandContext, new_password: str, old_password: str):
    """
    Used for changing the password of an already logged in user. If the password is forgotten,
    use the "reset_password" command.
    """
    if old_password is None:
        raise CommandFailed("You must provide your old password in order to change it.")

    user = context.runtime_user

    try:
        user.change_password(new_password, old_password)
    except InvalidPassword:
        raise CommandFailed("Invalid password.")

    return {'message': 'Your password has been changed.'}


@command("reset_password")
def reset_password(context: CommandContext, email: str):
    try:
        user = User.objects.get(email=email)
        user.change_password(new_password=None, old_password=None)
    finally:
        return {
            'message': 'If an user with the given email exists, then we have sent an email with the new password.'
        }


@command("verify")
@login_required
def verify(context: CommandContext, verification_number):
    user = context.runtime_user

    try:
        user.verify(verification_number)
    except UserVerificationError as e:
        raise CommandFailed(f"Verification failed: {e}")

    return {'message': 'You have successfully verified your email address.'}


@command("logout")
@login_required
def logout(context: CommandContext):
    user = context.runtime_user
    user.disconnect()
    context.runtime_user = None
    return {}


@command("add_balance")
@login_required
def add_balance(context: CommandContext, amount: Union[Decimal, float]):
    user = context.runtime_user
    amount = Decimal(amount)
    user.add_balance_transaction(amount)
    return {"current_balance": user.initial_balance}


@command("list_items")
@login_required
def list_items(context: CommandContext):
    user = context.runtime_user
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
def view_transaction_history(context: CommandContext):
    user = context.runtime_user
    return {"history": user.transaction_history}


@command("create_auction")
@login_required
def create_auction(
    context: CommandContext, item_id: int, bidding_strategy_identifier: str, **kwargs
):
    user = context.runtime_user

    # Coerce all floats to decimals
    for key, value in kwargs.items():
        if isinstance(value, float):
            kwargs[key] = Decimal(value)

    auction_id = user.create_auction(
        item_id=item_id,
        bidding_strategy_identifier=bidding_strategy_identifier,
        **kwargs,
    )
    auction = runtime_manager.active_auctions[auction_id]
    return {'auction': {**auction.to_json()}}


@command("start_auction")
@login_required
def start_auction(context: CommandContext, auction_id: int):
    user = context.runtime_user
    auction = runtime_manager.active_auctions[auction_id]

    if user.id == auction.owner.id:
        auction.start()
    else:
        raise CommandFailed(
            "You must be the owner of the auction to perform this action."
        )
    return {'auction': {**auction.to_json()}}


@command("bid")
@login_required
def bid(context: CommandContext, auction_id: int, amount: float):
    user = context.runtime_user
    amount = Decimal(amount)

    try:
        auction = runtime_manager.get_auction_by_id(auction_id)
        auction.bid(user, amount)
    except AuctionDoesNotExist as e:
        raise CommandFailed(f"Could not bid in auction: {e}")
    except BiddingNotAllowed as e:
        raise CommandFailed(f"Bidding not allowed: {e.reason.value}")
    return {'auction': {**auction.to_json()}}


@command("sell")
@login_required
def sell(context: CommandContext, auction_id: int):
    user = context.runtime_user

    try:
        auction = runtime_manager.get_auction_by_id(auction_id)
        if user.id == auction.owner.id:
            auction.sell()
        else:
            raise CommandFailed(
                "You must be the owner of the auction to perform this action."
            )
    except AuctionDoesNotExist as e:
        raise CommandFailed(f"Could not end auction: {e}")
    return {'auction': {**auction.to_json()}}


@command("view_auction_report")
@login_required
def view_auction_report(context: CommandContext, auction_id: int):
    try:
        auction = runtime_manager.get_auction_by_id(auction_id)
    except AuctionDoesNotExist as e:
        raise CommandFailed(f"Could not view auction report: {e}")
    return {'auction': {'report': auction.auction_report}}


@command("view_auction_history")
@login_required
def view_auction_history(context: CommandContext, auction_id: int):
    try:
        auction = runtime_manager.get_auction_by_id(auction_id)
    except AuctionDoesNotExist as e:
        raise CommandFailed(f"Could not view auction history: {e}")
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

        thread = threading.Thread(
            target=handle_commands, args=(new_socket, client_address)
        )
        thread.start()


@atexit.register
def cleanup_pazar():
    server_sock.close()

    logger.info("Terminated Pazar server", SERVER_PORT)


def extract_request_data(request_obj):
    try:
        command_identifier = request_obj['command']
        params = request_obj['params']
    except KeyError as e:
        raise InvalidCommand(f'Command has missing key: {e}')
    return command_identifier, params


def get_command_by_identifier(command_identifier):
    try:
        return COMMANDS[command_identifier]
    except KeyError as e:
        raise InvalidCommand(f'Command does not exist: {e}')


def encode_response(response_dict):
    response_str = json.dumps(
        response_dict, indent=4, sort_keys=True, cls=DjangoJSONEncoder
    )
    return response_str.encode()  # convert str to bytes


def handle_commands(sock, client_address):
    context = CommandContext()

    while data_in := sock.recv(BUFFER_SIZE):
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
            response = encode_response(command_result)
            sock.send(response)
            sock.close()
            return

        response = encode_response(command_result)
        sock.send(response)
