from collections import defaultdict
from decimal import Decimal
from operator import itemgetter
from threading import Timer

from bidpazari.core.exceptions import (
    BiddingErrorReason,
    BiddingNotAllowed,
    InsufficientBalanceError,
)
from bidpazari.core.helpers import serialize_user
from bidpazari.core.models import Transaction
from bidpazari.core.templatetags.core.tags import money


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

    def bid(self, bidder, amount):
        self.auction.log_event(
            f"{bidder.persistent_user.get_full_name()} made a bid: {amount}"
        )
        self.auction.on_bidding_updated(
            type="bid_received",
            data={'bidder': serialize_user(bidder.persistent_user), 'amount': amount},
        )
        self.bidders.add(bidder)
        self.bidding_history.append((bidder, amount))

    def get_current_winner_and_amount(self):
        raise NotImplementedError

    def get_current_price(self):
        raise NotImplementedError

    def get_tooltip_text(self):
        raise NotImplementedError

    def get_human_readable_parameters(self):
        raise NotImplementedError


class IncrementBiddingStrategy(BaseBiddingStrategy):
    def __init__(
        self, initial_price, minimum_increment=Decimal(1.0), maximum_price=None
    ):
        super().__init__()
        self.initial_price = initial_price
        self.minimum_increment = minimum_increment
        self.maximum_price = maximum_price
        self.highest_bid = initial_price
        self.highest_bidder = None
        # TODO Refactor this to be bidding_history itself.
        self.bids_by_user = defaultdict(Decimal)

    def reserve_for_bid(self, bidder, amount):
        if amount < self.highest_bid:
            raise BiddingNotAllowed(BiddingErrorReason.InsufficientAmount)
        if amount - self.highest_bid < self.minimum_increment:
            raise BiddingNotAllowed(BiddingErrorReason.InsufficientAmount)

        super().reserve_for_bid(bidder, amount)

    def stop(self):
        for bidder in self.bidders:
            amount = self.bids_by_user[bidder]
            bidder.unreserve_balance(amount)
            self.bids_by_user[bidder] = Decimal('0')

        super().stop()

    def bid(self, bidder: "RuntimeUser", amount):
        past_bidding_amount = self.bids_by_user[bidder]
        bidder.unreserve_balance(past_bidding_amount)
        self.bids_by_user[bidder] = Decimal('0')

        try:
            self.reserve_for_bid(bidder, amount)
        except:
            bidder.reserve_balance(past_bidding_amount)
            raise

        super().bid(bidder, amount)  # log to bidding history
        self.bids_by_user[bidder] += amount
        # This must be the highest bid, since no other bids are allowed.
        self.highest_bid = amount
        self.highest_bidder = bidder

        if self.maximum_price and self.maximum_price <= self.highest_bid:
            self.stop()

    def get_current_winner_and_amount(self):
        if self.highest_bidder:
            return self.highest_bidder, self.highest_bid
        return None, None

    def get_current_price(self):
        return self.highest_bid + self.minimum_increment

    def get_tooltip_text(self):
        return (
            "Bids are gradually incremented by the minimum increment. "
            "Auction will stop when the maximum price is reached."
        )

    def get_human_readable_parameters(self):
        return {
            'Initial price': money(self.initial_price),
            'Minimum increment': money(self.minimum_increment),
            'Maximum price': money(self.maximum_price),
        }


class DecrementBiddingStrategy(BaseBiddingStrategy):
    def __init__(
        self,
        initial_price,
        minimum_price=Decimal(0.0),
        price_decrement_rate=Decimal(1.0),
        tick_ms=1000,
    ):
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
        self.tick_s = tick_ms / 1000
        self.decrementing_thread = Timer(self.tick_s, self._decrement_price)

    def _decrement_price(self):
        from bidpazari.core.runtime.auction import AuctionStatus

        should_decrement = (self.auction.status == AuctionStatus.OPEN) and (
            self.current_price > self.minimum_price
        )

        if should_decrement:
            self.current_price = max(
                self.current_price - self.price_decrement_rate, self.minimum_price
            )
            self.auction.on_bidding_updated(
                type="price_decremented",
                data={'current_price': self.get_current_price()},
            )
            self.decrementing_thread = Timer(self.tick_s, self._decrement_price)
            self.decrementing_thread.start()
        elif not self.auction.status == AuctionStatus.CLOSED:
            self.stop()

    def start(self):
        self.decrementing_thread.start()

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

    def get_tooltip_text(self):
        return (
            "The price gradually decreases over time. First bidder wins. "
            "Auction is closed when the minimum price is reached."
        )

    def get_human_readable_parameters(self):
        price_decrement_rate_money = money(self.price_decrement_rate)
        return {
            'Initial price': money(self.initial_price),
            'Minimum price': money(self.minimum_price),
            'Price decrement rate': f'{price_decrement_rate_money} every {self.tick_s} seconds',
        }


class HighestContributionBiddingStrategy(BaseBiddingStrategy):
    def __init__(self, minimum_bid_amount=Decimal(1.0), maximum_price=None):
        super().__init__()
        self.minimum_bid_amount = minimum_bid_amount
        self.maximum_price = maximum_price
        self.current_price = Decimal(0.0)

    def reserve_for_bid(self, bidder, amount):
        if amount < self.minimum_bid_amount:
            raise BiddingNotAllowed(BiddingErrorReason.InsufficientAmount)

        super().reserve_for_bid(bidder, amount)

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
                Transaction.objects.create(
                    source=loser.persistent_user,
                    destination=self.auction.owner,
                    amount=lost_amount,
                    item=self.auction.item,
                )

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

    def get_tooltip_text(self):
        return (
            "Auction is open until the target price is reached. "
            "The bidder with the highest contribution wins. "
            "The pooled bids are not returned to the losing bidders."
        )

    def get_human_readable_parameters(self):
        return {
            'Minimum bid amount': money(self.minimum_bid_amount),
            'Maximum price': money(self.maximum_price),
        }


class BiddingStrategyFactory:
    BIDDING_STRATEGY_TYPES = {
        "increment": IncrementBiddingStrategy,
        "decrement": DecrementBiddingStrategy,
        "highest_contribution": HighestContributionBiddingStrategy,
    }

    BIDDING_STRATEGY_HUMAN_READABLE = {
        "increment": "Increment Bidding",
        "decrement": "Decrement Bidding",
        "highest_contribution": "Highest Contribution Bidding",
    }

    @classmethod
    def get(cls, identifier: str, **kwargs) -> BaseBiddingStrategy:
        klass = cls.BIDDING_STRATEGY_TYPES[identifier]
        return klass(**kwargs)
