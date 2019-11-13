from collections import defaultdict
from operator import itemgetter
from threading import Thread
from time import sleep

from core.exceptions import BiddingNotAllowed, BiddingErrorReason


class BaseBiddingStrategy:
    def __init__(self):
        self.bidding_history = []

    def start(self):
        pass

    def stop(self):
        return self.get_current_winner()

    def bid(self, bidder, amount):
        self.bidding_history.append((bidder, amount))

    def get_current_winner(self):
        raise NotImplementedError

    def get_current_price(self):
        raise NotImplementedError


class IncrementBiddingStrategy(BaseBiddingStrategy):
    def __init__(self, initial_price, minimum_increment=1.0, maximum_price=None):
        super().__init__()
        self.minimum_increment = minimum_increment
        self.maximum_price = maximum_price
        self.highest_bid = initial_price
        self.highest_bidder = None

    def _check_bid_possible(self, bidder, amount):
        if amount < self.highest_bid:
            raise BiddingNotAllowed(BiddingErrorReason.InsufficientAmount)
        if amount - self.highest_bid < self.minimum_increment:
            raise BiddingNotAllowed(BiddingErrorReason.InsufficientAmount)
        if self.maximum_price and amount > self.maximum_price:
            raise BiddingNotAllowed(BiddingErrorReason.AmountTooHigh)

    def bid(self, bidder, amount):
        self._check_bid_possible(bidder, amount)

        super().bid(bidder, amount)  # log to bidding history
        self.highest_bid = amount
        self.highest_bidder = bidder

        if self.maximum_price and self.maximum_price <= self.highest_bid:
            self.stop()

    def get_current_winner(self):
        return self.highest_bidder

    def get_current_price(self):
        return self.highest_bid


class DecrementBiddingStrategy(BaseBiddingStrategy):
    def __init__(self, initial_price, minimum_price=0.0, price_decrement_rate=1.0, tick_ms=1000):
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
        self.decrement_flag = False

    def _start_price_decrement(self):
        self.decrement_flag = True
        self.decrementing_thread.start()

    def _stop_price_decrement(self):
        self.decrement_flag = False
        self.decrementing_thread.join()

    def start(self):
        self._start_price_decrement()

    def stop(self):
        self._stop_price_decrement()
        return super().stop()

    def bid(self, bidder, amount=None):
        self.stop()
        super().bid(bidder, self.get_current_price())

    def get_current_winner(self):
        if len(self.bidding_history) == 1:
            bidder, _ = self.bidding_history[0]
            return bidder
        return None

    def get_current_price(self):
        return self.current_price


class HighestContributionBiddingStrategy(BaseBiddingStrategy):
    def __init__(self, minimum_bid_amount=1.0, maximum_price=None):
        super().__init__()
        self.minimum_bid_amount = minimum_bid_amount
        self.maximum_price = maximum_price
        self.current_price = 0.0

    def _check_bid_possible(self, bidder, amount):
        if amount < self.minimum_bid_amount:
            raise BiddingNotAllowed(BiddingErrorReason.InsufficientAmount)
        if amount + self.current_price > self.maximum_price:
            raise BiddingNotAllowed(BiddingErrorReason.AmountTooHigh)

    def bid(self, bidder, amount):
        self._check_bid_possible(bidder, amount)

        self.current_price += amount

        if self.current_price >= self.maximum_price:
            self.stop()

        super().bid(bidder, amount)

    def get_current_winner(self):
        if not self.bidding_history:
            return None

        totals_per_bidder = defaultdict(float)

        for bidder, amount in self.bidding_history:
            totals_per_bidder[bidder] += amount

        highest_bidder, _ = max(totals_per_bidder.items(), key=itemgetter(1))
        return highest_bidder

    def get_current_price(self):
        return self.current_price
