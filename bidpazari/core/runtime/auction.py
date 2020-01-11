from decimal import Decimal

from django.utils import timezone
from django.utils.functional import cached_property

from bidpazari.core.exceptions import (
    BiddingErrorReason,
    BiddingNotAllowed,
    InsufficientBalanceError,
)
from bidpazari.core.helpers import (
    get_human_readable_activity_message,
    serialize_user,
)
from bidpazari.core.models import Transaction, UserHasItem
from bidpazari.core.runtime.exceptions import InvalidAuctionStatus
from bidpazari.core.runtime.strategies import BiddingStrategyFactory
from bidpazari.core.runtime.watchers import AuctionWatcher
from bidpazari.core.templatetags.core.tags import money


class AuctionStatus:
    INITIAL = 'INITIAL'
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'


class Auction:
    def __init__(self, uhi: UserHasItem, bidding_strategy_identifier: str, **kwargs):
        self.uhi = uhi
        self.bidding_strategy_identifier = bidding_strategy_identifier
        self.bidding_strategy = BiddingStrategyFactory.get(
            bidding_strategy_identifier, **kwargs
        )
        self.bidding_strategy.auction = self
        self.status = AuctionStatus.INITIAL
        self.auction_watchers = []
        self.activity_log_v2 = []
        self.activity_log = []  # TODO remove this
        self.log_event("Auction created")

    @property
    def id(self):
        return self.uhi.id

    @cached_property
    def owner(self):
        return self.uhi.user

    @cached_property
    def item(self):
        return self.uhi.item

    def start(self):
        if self.status != AuctionStatus.INITIAL:
            raise InvalidAuctionStatus(
                "You can perform this action only on auctions which have not yet been started."
            )

        self.status = AuctionStatus.OPEN
        self.bidding_strategy.start()
        self.on_bidding_updated(
            type="auction_started",
            data={'current_price': self.bidding_strategy.get_current_price()},
        )
        self.log_event("Auction started")

    def stop(self):
        self.bidding_strategy.stop()

    def sell(self):
        self.log_event("Auction ended manually by owner")
        self.stop()

    def on_bidding_updated(self, *args, **kwargs):
        msg = get_human_readable_activity_message({**kwargs})
        self.activity_log_v2.append({**kwargs, 'ts': timezone.now(), 'msg': msg})
        self.notify_users(*args, **kwargs)

    def on_bidding_stopped(self):
        if self.status == AuctionStatus.CLOSED:
            raise InvalidAuctionStatus('Auction has already been stopped.')

        self.status = AuctionStatus.CLOSED
        self.log_event("Auction stopped")

        winner, amount = self.bidding_strategy.get_current_winner_and_amount()

        if winner:
            UserHasItem.objects.create(user=winner.persistent_user, item=self.item)
            Transaction.objects.create(
                source=winner.persistent_user,
                destination=self.owner,
                item=self.item,
                amount=amount,
            )

            self.uhi.is_sold = True
            self.uhi.save()

            self.log_event(
                f"Winner: {winner.persistent_user.get_full_name()} for amount: {amount}"
            )
        else:
            self.log_event("Auction reached minimum price with no bidders.")

        self.item.on_sale = False
        self.item.save()

        self.on_bidding_updated(
            type="auction_stopped",
            data={
                'winner': winner and serialize_user(winner.persistent_user),
                'amount': amount,
            },
        )

    def bid(self, user: "RuntimeUser", amount=None):
        if self.status != AuctionStatus.OPEN:
            raise BiddingNotAllowed(BiddingErrorReason.AuctionClosed)

        if user.id == self.owner.id:
            raise BiddingNotAllowed(BiddingErrorReason.OwnAuction)

        try:
            self.bidding_strategy.bid(user, amount)
        except InsufficientBalanceError:
            raise
        except BiddingNotAllowed:
            raise

    @property
    def auction_report(self):
        data = self.to_json()

        return f"""\
Auction Report
==============
Auction Status: {data['status']}
Bidding Strategy: {data['bidding_strategy']}
Item: {data['item']}
Description: {data['description']}
Owner: {data['owner']}
Current Price: {data['current_price']}
{data['current_winner']}
Winning Amount: {data['winning_amount']}


Bidding Details
===============
{data['bidding_details']}
"""

    def to_json(self):
        (
            current_winner,
            winning_amount,
        ) = self.bidding_strategy.get_current_winner_and_amount()
        bidding_strategy_name = BiddingStrategyFactory.BIDDING_STRATEGY_HUMAN_READABLE[
            self.bidding_strategy_identifier
        ]

        if current_winner:
            current_winner_name = current_winner.persistent_user.get_full_name()
            current_winner_line = f"Current Winner: {current_winner_name}"
        else:
            current_winner_line = "Nobody is currently winning."

        return {
            'id': self.id,
            'status': self.status,
            'bidding_strategy': bidding_strategy_name,
            'item_image': str(self.item.image),
            'item': self.item.title,
            'description': self.item.description,
            'item_type': self.item.item_type,
            'owner': self.owner.get_full_name(),
            'current_price': money(self.bidding_strategy.get_current_price()),
            'current_winner': current_winner_line,
            'winning_amount': winning_amount,
            'bidding_details': self.bidding_strategy.get_tooltip_text(),
        }

    def to_django(self):
        (
            current_winner,
            winning_amount,
        ) = self.bidding_strategy.get_current_winner_and_amount()
        bidding_strategy_name = BiddingStrategyFactory.BIDDING_STRATEGY_HUMAN_READABLE[
            self.bidding_strategy_identifier
        ]

        if current_winner:
            current_winner = current_winner.persistent_user.get_full_name()
        else:
            current_winner = 'Nobody'

        return {
            'id': self.id,
            'status': self.status,
            'item': self.item,
            'owner': self.owner,
            'bidding_strategy': bidding_strategy_name,
            'bidding_strategy_params': self.bidding_strategy.get_human_readable_parameters(),
            'bidding_strategy_help': self.bidding_strategy.get_tooltip_text(),
            'current_winner': current_winner,
            'current_price': self.bidding_strategy.get_current_price(),
            'winning_amount': winning_amount,
            'activity': list(reversed(self.activity_log_v2)),
        }

    def register_user_to_updates(self, callback_method):
        auction_watcher = AuctionWatcher(callback_method)
        self.auction_watchers.append(auction_watcher)

    def notify_users(self, *args, **kwargs):
        for auction_watcher in self.auction_watchers:
            auction_watcher.notify(*args, **kwargs)

    def log_event(self, message: str):
        self.activity_log.append(f"{timezone.now()} -- {message}")

    @property
    def auction_history(self):
        log_text = "\n".join(self.activity_log)
        return f"""\
Auction History
===============
{log_text}"""

    @property
    def initial_price(self):
        try:
            return self.bidding_strategy.initial_price
        except AttributeError:
            return Decimal(0)
