import asyncio
import time
from decimal import Decimal
from typing import Optional, Union

from bidpazari.core.exceptions import (
    BiddingNotAllowed,
    InvalidPassword,
    UserVerificationError,
)
from bidpazari.core.models import User
from bidpazari.core.runtime.common import runtime_manager
from bidpazari.core.runtime.exceptions import (
    AuctionDoesNotExist,
    InvalidAuctionStatus,
)
from bidpazari.core.runtime.net.decorators import command, login_required
from bidpazari.core.runtime.net.exceptions import CommandFailed, InvalidCommand
from bidpazari.core.runtime.user import RuntimeUser

COMMANDS = {}


def get_command_by_identifier(command_identifier):
    try:
        return COMMANDS[command_identifier]
    except KeyError as e:
        raise InvalidCommand(f'Command does not exist: {e}')


class CommandContext:
    """
    Container class for everything required to run a command. Passed as the first parameter
    of every command function.
    """

    def __init__(self, runtime_user: RuntimeUser = None):
        self.runtime_user = runtime_user


@command("create_user")
async def create_user(
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
async def login(context: CommandContext, username: str, password: str):
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
async def change_password(
    context: CommandContext, new_password: str, old_password: str
):
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
async def reset_password(context: CommandContext, email: str):
    try:
        user = User.objects.get(email=email)
        user.change_password(new_password=None, old_password=None)
    finally:
        return {
            'message': 'If an user with the given email exists, then we have sent an email with the new password.'
        }


@command("verify")
@login_required
async def verify(context: CommandContext, verification_number):
    user = context.runtime_user

    try:
        user.verify(verification_number)
    except UserVerificationError as e:
        raise CommandFailed(f"Verification failed: {e}")

    return {'message': 'You have successfully verified your email address.'}


@command("logout")
@login_required
async def logout(context: CommandContext):
    user = context.runtime_user
    user.disconnect()
    context.runtime_user = None
    return {}


@command("add_balance")
@login_required
async def add_balance(context: CommandContext, amount: Union[Decimal, float]):
    user = context.runtime_user
    amount = Decimal(amount)
    user.add_balance_transaction(amount)
    return {"current_balance": user.initial_balance}


@command("list_items")
@login_required
async def list_items(
    context: CommandContext, item_type: Optional[str], on_sale: Optional[bool]
):
    user = context.runtime_user
    return {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "on_sale": item.on_sale,
            }
            for item in user.list_items(item_type=item_type, on_sale=on_sale)
        ]
    }


@command("view_transaction_history")
@login_required
async def view_transaction_history(context: CommandContext):
    user = context.runtime_user
    return {"history": user.transaction_history}


@command("create_auction")
@login_required
async def create_auction(
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
    auction = runtime_manager.get_auction_by_id(auction_id)
    return {'auction': {**auction.to_json()}}


@command("start_auction")
@login_required
async def start_auction(context: CommandContext, auction_id: int):
    user = context.runtime_user

    try:
        auction = runtime_manager.get_auction_by_id(auction_id)
    except AuctionDoesNotExist as e:
        raise CommandFailed(f"Could not start auction: {e}")

    if user.id == auction.owner.id:
        try:
            auction.start()
        except InvalidAuctionStatus as e:
            raise CommandFailed(f"Could not start auction: {e}")
    else:
        raise CommandFailed(
            "You must be the owner of the auction to perform this action."
        )
    return {'auction': {**auction.to_json()}}


@command("bid")
@login_required
async def bid(context: CommandContext, auction_id: int, amount: float):
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
async def sell(context: CommandContext, auction_id: int):
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
async def view_auction_report(context: CommandContext, auction_id: int):
    try:
        auction = runtime_manager.get_auction_by_id(auction_id)
    except AuctionDoesNotExist as e:
        raise CommandFailed(f"Could not view auction report: {e}")
    return {'auction': {'report': auction.auction_report}}


@command("view_auction_history")
@login_required
async def view_auction_history(context: CommandContext, auction_id: int):
    try:
        auction = runtime_manager.get_auction_by_id(auction_id)
    except AuctionDoesNotExist as e:
        raise CommandFailed(f"Could not view auction history: {e}")
    return {'auction': {'report': auction.auction_history}}


def extract_request_data(request_obj):
    try:
        command_identifier = request_obj['command']
        params = request_obj['params']
    except KeyError as e:
        raise InvalidCommand(f'Command has missing key: {e}')
    return command_identifier, params
