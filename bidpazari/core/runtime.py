from collections import defaultdict
from decimal import Decimal
from functools import wraps
from operator import itemgetter
from threading import Thread
from time import sleep

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property

from bidpazari.core.exceptions import (BiddingErrorReason, BiddingNotAllowed,
                                       InsufficientBalanceError,
                                       NonPersistentObjectError)
from bidpazari.core.models import Item, Transaction, User, UserHasItem


def persistent_user_proxy_method(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        if not self.persistent_user:
            raise NonPersistentObjectError(f'{fn.__name__} must be called on a persisted user')
        return fn(self, *args, **kwargs)
    return wrapper


class BaseBiddingStrategy:
    def __init__(self):
        self.bidders = set()
        self.bidding_history = []
        self.auction = None

    def reserve_for_bid(self, bidder, amount):
        try:
            bidder.reserve_balance(amount)
        except InsufficientBalanceError:
            raise

    def start(self):
        pass

    def stop(self):
        self.auction.on_bidding_stopped()

    def cleanup(self):
        pass

    def bid(self, bidder, amount):
        self.auction.log_event(f'{bidder.persistent_user.get_full_name()} made a bid: {amount}')
        self.auction.on_bidding_updated(event_type='bid_received')
        self.bidders.add(bidder)
        self.bidding_history.append((bidder, amount))

    def get_current_winner_and_amount(self):
        raise NotImplementedError

    def get_current_price(self):
        raise NotImplementedError

    def get_auction_report_text(self):
        raise NotImplementedError


class IncrementBiddingStrategy(BaseBiddingStrategy):
    def __init__(self, initial_price, minimum_increment=Decimal(1.0), maximum_price=None):
        super().__init__()
        self.minimum_increment = minimum_increment
        self.maximum_price = maximum_price
        self.highest_bid = initial_price
        self.highest_bidder = None

    def reserve_for_bid(self, bidder, amount):
        super().reserve_for_bid(bidder, amount)

        if amount < self.highest_bid:
            raise BiddingNotAllowed(BiddingErrorReason.InsufficientAmount)
        if amount - self.highest_bid < self.minimum_increment:
            raise BiddingNotAllowed(BiddingErrorReason.InsufficientAmount)

    def stop(self):
        for bidder in self.bidders:
            bidder.unreserve_all()

        super().stop()

    def bid(self, bidder: 'RuntimeUser', amount):
        bidder.unreserve_all()
        self.reserve_for_bid(bidder, amount)

        super().bid(bidder, amount)  # log to bidding history
        self.highest_bid = amount
        self.highest_bidder = bidder

        if self.maximum_price and self.maximum_price <= self.highest_bid:
            self.stop()

    def get_current_winner_and_amount(self):
        if self.highest_bidder:
            return self.highest_bidder, self.highest_bid
        return None, None

    def get_current_price(self):
        return self.highest_bid

    def get_auction_report_text(self):
        return f'Maximum Price: {self.maximum_price}.\n' \
               f'Auction will stop when this bid is reached.\n'


class DecrementBiddingStrategy(BaseBiddingStrategy):
    def __init__(self,
                 initial_price,
                 minimum_price=Decimal(0.0),
                 price_decrement_rate=Decimal(1.0),
                 tick_ms=1000):
        """
        Comment this later.
        :param initial_price:
        :param price_decrement_rate: $/sec
        """
        super().__init__()
        self.initial_price = initial_price
        self.current_price = initial_price
        self.minimum_price = minimum_price
        self.price_decrement_rate = price_decrement_rate
        self.tick_ms = tick_ms
        self.decrementing_thread = Thread(target=self._decrement_price)
        self.decrement_flag = False

    def _decrement_price(self):
        should_decrement \
            = lambda: self.decrement_flag and (self.current_price > self.minimum_price)
        tick_s = self.tick_ms / 1000

        while should_decrement():
            sleep(tick_s)
            self.current_price = max(self.current_price - self.price_decrement_rate,
                                     self.minimum_price)
            self.auction.on_bidding_updated(event_type='price_decremented',
                                            new_price=self.current_price)
        # TODO fix stopping automatically behavior here

    def start(self):
        self.decrement_flag = True
        self.decrementing_thread.start()

    def stop(self):
        self.decrement_flag = False
        self.decrementing_thread.join()
        super().stop()

    def cleanup(self):
        pass

    def bid(self, bidder, amount=None):
        self.reserve_for_bid(bidder, self.get_current_price())
        super().bid(bidder, self.get_current_price())
        self.stop()

    def get_current_winner_and_amount(self):
        if len(self.bidding_history) == 1:
            bidder, amount = self.bidding_history[0]
            return bidder, amount
        return None, None

    def get_current_price(self):
        return self.current_price

    def get_auction_report_text(self):
        return f'Minimum Price: {self.minimum_price}.\n' \
               f'Auction will stop when this bid is reached.\n' \
               f'The first bidder to buy wins.\n'


class HighestContributionBiddingStrategy(BaseBiddingStrategy):
    def __init__(self, minimum_bid_amount=Decimal(1.0), maximum_price=None):
        super().__init__()
        self.minimum_bid_amount = minimum_bid_amount
        self.maximum_price = maximum_price
        self.current_price = Decimal(0.0)

    def reserve_for_bid(self, bidder, amount):
        super().reserve_for_bid(bidder, amount)

        if amount < self.minimum_bid_amount:
            raise BiddingNotAllowed(BiddingErrorReason.InsufficientAmount)

    def bid(self, bidder, amount):
        self.reserve_for_bid(bidder, amount)

        self.current_price += amount

        super().bid(bidder, amount)

        if self.current_price >= self.maximum_price:
            self.stop()

    def stop(self):
        totals = self.totals_per_bidder

        if totals:
            highest_bidder, _ = max(self.totals_per_bidder.items(), key=itemgetter(1))
            totals.pop(highest_bidder)

            for loser, lost_amount in totals.items():
                Transaction.objects.create(source=loser.persistent_user,
                                           destination=self.auction.owner,
                                           amount=lost_amount,
                                           item=self.auction.item)

        super().stop()

    @property
    def totals_per_bidder(self):
        if not self.bidding_history:
            return {}

        totals = defaultdict(Decimal)

        for bidder, amount in self.bidding_history:
            totals[bidder] += amount

        return dict(totals)

    def get_current_winner_and_amount(self):
        if not self.bidding_history:
            return None, None

        highest_bidder, amount = max(self.totals_per_bidder.items(), key=itemgetter(1))
        return highest_bidder, amount

    def get_current_price(self):
        return self.current_price

    def get_auction_report_text(self):
        return f'Maximum Price: {self.maximum_price}.\n' \
               f'Auction will stop when this bid is reached.\n' \
               f'The bidder with the highest contribution wins.\n'


class BiddingStrategyFactory:
    BIDDING_STRATEGY_TYPES = {
        'increment': IncrementBiddingStrategy,
        'decrement': DecrementBiddingStrategy,
        'highest_contribution': HighestContributionBiddingStrategy
    }

    BIDDING_STRATEGY_HUMAN_READABLE = {
        'increment': 'Increment Bidding',
        'decrement': 'Decrement Bidding',
        'highest_contribution': 'Highest Contribution Bidding'
    }

    @classmethod
    def get(cls, identifier: str, **kwargs) -> BaseBiddingStrategy:
        klass = cls.BIDDING_STRATEGY_TYPES[identifier]
        return klass(**kwargs)


class Watcher:
    pass


class ItemWatcher(Watcher):
    def __init__(self, callback_method, item_type=None):
        self.callback_method = callback_method
        self.item_type = item_type

    def notify(self, item: Item, initial_price):
        if not self.item_type or self.item_type == item.item_type:
            self.callback_method(item, initial_price)


class AuctionWatcher(Watcher):
    def __init__(self, callback_method):
        self.callback_method = callback_method

    def notify(self, *args, **kwargs):
        self.callback_method(*args, **kwargs)


class RuntimeManager:
    def __init__(self):
        self.active_auctions = {}
        self.item_watchers = []
        self.online_users = set()

    def create_auction(self, uhi: UserHasItem,
                       bidding_strategy_identifier: str,
                       **kwargs):
        auction = Auction(uhi=uhi,
                          bidding_strategy_identifier=bidding_strategy_identifier,
                          **kwargs)
        self.active_auctions[uhi.id] = auction
        self.notify_users_of_new_auction(auction)
        return auction

    def notify_users_of_new_auction(self, auction):
        for item_watcher in self.item_watchers:
            item_watcher.notify(auction.item, auction.initial_price)

    def register_item_watcher(self, item_watcher):
        self.item_watchers.append(item_watcher)


runtime_manager = RuntimeManager()


class Auction:
    def __init__(self,
                 uhi: UserHasItem,
                 bidding_strategy_identifier: str,
                 **kwargs):
        self.uhi = uhi
        self.bidding_strategy_identifier = bidding_strategy_identifier
        self.bidding_strategy = BiddingStrategyFactory.get(bidding_strategy_identifier,
                                                           **kwargs)
        self.bidding_strategy.auction = self
        self.is_open = False
        self.auction_watchers = []
        self.activity_log = []
        self.log_event('Auction created')

    @cached_property
    def owner(self):
        return self.uhi.user

    @cached_property
    def item(self):
        return self.uhi.item

    def start(self):
        self.is_open = True
        self.bidding_strategy.start()
        self.on_bidding_updated(event_type='auction_started')
        self.log_event('Auction started')

    def stop(self):
        self.bidding_strategy.stop()

    def sell(self):
        self.log_event('Auction ended manually by owner')
        self.stop()

    def on_bidding_updated(self, *args, **kwargs):
        self.notify_users(*args, **kwargs)

    def on_bidding_stopped(self):
        self.bidding_strategy.cleanup()
        self.on_bidding_updated(event_type='auction_stopped')
        self.is_open = False
        self.log_event('Auction stopped')

        winner, amount = self.bidding_strategy.get_current_winner_and_amount()

        if winner:
            UserHasItem.objects.create(user=winner.persistent_user, item=self.item)
            Transaction.objects.create(source=winner.persistent_user,
                                       destination=self.owner,
                                       item=self.item,
                                       amount=amount)

            self.uhi.is_sold = True
            self.uhi.save()

            self.log_event(f'Winner: {winner.persistent_user.get_full_name()} for amount: {amount}')
        else:
            self.log_event('Auction reached minimum price with no bidders.')

        self.log_event('Removing auction from active auctions...')
        del runtime_manager.active_auctions[self.uhi.id]  # Unregister from runtime

    def bid(self, user: 'RuntimeUser', amount=None):
        if not self.is_open:
            raise BiddingNotAllowed(BiddingErrorReason.AuctionClosed)

        if user.id == self.owner.id:
            raise BiddingNotAllowed(BiddingErrorReason.OwnAuction)

        try:
            self.bidding_strategy.bid(user, amount)
        except InsufficientBalanceError:
            raise
        except BiddingNotAllowed:
            user.unreserve_balance(amount)
            raise

    @property
    def auction_report(self):
        current_winner, winning_amount = self.bidding_strategy.get_current_winner_and_amount()
        bidding_strategy_name = \
            BiddingStrategyFactory \
            .BIDDING_STRATEGY_HUMAN_READABLE[self.bidding_strategy_identifier]

        if current_winner:
            current_winner_name = current_winner.persistent_user.get_full_name()
            current_winner_line = f'Current Winner: {current_winner_name}'
        else:
            current_winner_line = 'Nobody is currently winning.'

        return f"""\
Auction Report
==============
Auction Status: {'Open' if self.is_open else 'Closed'}
Bidding Strategy: {bidding_strategy_name}
Item: {self.item.title}
Description: {self.item.description}
Owner: {self.owner.get_full_name()}
Current Price: {self.bidding_strategy.get_current_price()}
{current_winner_line}
Winning Amount: {winning_amount}


Bidding Details
===============
{self.bidding_strategy.get_auction_report_text()}
"""

    def register_user_to_updates(self, callback_method):
        auction_watcher = AuctionWatcher(callback_method)
        self.auction_watchers.append(auction_watcher)

    def notify_users(self, *args, **kwargs):
        for auction_watcher in self.auction_watchers:
            auction_watcher.notify(*args, **kwargs)

    def log_event(self, message: str):
        self.activity_log.append(f'{timezone.now()} -- {message}')

    @property
    def auction_history(self):
        log_text = '\n'.join(self.activity_log)
        return f'''\
Auction History
===============
{log_text}'''

    @property
    def initial_price(self):
        try:
            return self.bidding_strategy.initial_price
        except AttributeError:
            return Decimal(0)


class RuntimeUser:
    def __init__(self, username, email, password_raw, *, first_name, last_name):
        self.username = username
        self.email = email
        self._password = password_raw
        self.first_name = first_name
        self.last_name = last_name
        self.persistent_user = None
        self.initial_balance = Decimal(0)
        self.reserved_balance = Decimal(0)

    """
    Persistence methods
    """
    def persist(self):
        if self.persistent_user:
            return
        self.persistent_user = \
            User.objects.create_user(self.username, self.email, self._password,
                                     first_name=self.first_name, last_name=self.last_name)

    @classmethod
    def from_persistent_user(cls, user: User):
        runtime_user = cls(user.username, user.email, password_raw=None,
                           first_name=user.first_name, last_name=user.last_name)
        runtime_user.persistent_user = user
        runtime_user.initial_balance = user.balance
        return runtime_user

    @cached_property
    @persistent_user_proxy_method
    def id(self):
        return self.persistent_user.id

    """
    Proxy methods
    """
    @persistent_user_proxy_method
    def verify(self, verification_number):
        self.persistent_user.verify(verification_number)

    @persistent_user_proxy_method
    def change_password(self, new_password, old_password=None):
        return self.persistent_user.change_password(new_password, old_password)

    @persistent_user_proxy_method
    def list_items(self, item_type=None, on_sale=None):
        return set(self.persistent_user.list_items(item_type, on_sale))

    @persistent_user_proxy_method
    def add_balance_transaction(self, amount):
        self.persistent_user.add_balance(amount)
        self.initial_balance = self.persistent_user.balance

    @property
    @persistent_user_proxy_method
    def transaction_history(self):
        return self.persistent_user.transaction_history

    """
    Runtime specific methods
    """
    @staticmethod
    def register_item_watcher(callback_method, item_type=None):
        item_watcher = ItemWatcher(callback_method, item_type=item_type)
        runtime_manager.register_item_watcher(item_watcher)

    @property
    def reservable_balance(self):
        return self.initial_balance - self.reserved_balance

    def reserve_balance(self, amount):
        if amount > self.reservable_balance:
            raise InsufficientBalanceError("Amount is higher than reservable balance.")
        self.reserved_balance += amount

    def unreserve_balance(self, amount):
        if amount > self.reserved_balance:
            raise InsufficientBalanceError("Amount is higher than reserved balance.")
        self.reserved_balance -= amount

    def unreserve_all(self):
        self.reserved_balance = Decimal(0)

    def connect(self):
        runtime_manager.online_users.add(self)

    def disconnect(self):
        runtime_manager.online_users.remove(self)

    """
    Magic methods
    """
    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return isinstance(other, RuntimeUser) and self.id == other.id


@receiver(post_save, sender=Transaction)
def update_balances_of_runtime_users(sender, instance: Transaction, **kwargs):
    if not kwargs['created']:
        return

    source_user = instance.source
    destination_user = instance.destination

    for user in runtime_manager.online_users:
        if source_user and user.id == source_user.id:
            user.initial_balance = source_user.balance
        elif user.id == destination_user.id:
            user.initial_balance = destination_user.balance
