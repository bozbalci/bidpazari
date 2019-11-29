from decimal import Decimal
from time import sleep
from unittest.mock import Mock

from django.test import TestCase

from bidpazari.core.exceptions import (
    BiddingErrorReason,
    BiddingNotAllowed,
    InsufficientBalanceError,
)
from bidpazari.core.runtime.strategies import (
    DecrementBiddingStrategy,
    HighestContributionBiddingStrategy,
    IncrementBiddingStrategy,
)
from bidpazari.core.runtime.user import RuntimeUser


class IncrementBiddingStrategyTestCase(TestCase):
    def test_bid_success(self):
        strategy = IncrementBiddingStrategy(initial_price=Decimal(3.00))
        strategy.auction = Mock()

        strategy.start()

        bidder_1 = Mock(reserved_balance=Decimal(10))
        bidder_2 = Mock(reserved_balance=Decimal(20))
        strategy.bid(bidder=bidder_1, amount=Decimal(5))
        strategy.bid(bidder=bidder_2, amount=Decimal(6))
        strategy.stop()

        self.assertIn((bidder_1, Decimal(5)), strategy.bidding_history)
        self.assertIn((bidder_2, Decimal(6)), strategy.bidding_history)
        self.assertEqual(strategy.highest_bid, Decimal(6))
        self.assertEqual(strategy.highest_bidder, bidder_2)

    def test_bid_lower_than_initial_price_fails(self):
        strategy = IncrementBiddingStrategy(initial_price=Decimal(3.00))
        strategy.auction = Mock()
        strategy.start()

        bidder_1 = Mock(reserved_balance=Decimal(10))

        with self.assertRaises(BiddingNotAllowed) as cm:
            strategy.bid(bidder=bidder_1, amount=Decimal(2))
        self.assertEqual(cm.exception.reason, BiddingErrorReason.InsufficientAmount)

        strategy.stop()

    def test_bid_incrementing_less_than_allowed_amount_fails(self):
        strategy = IncrementBiddingStrategy(
            initial_price=Decimal(3.00), minimum_increment=Decimal(2)
        )
        strategy.auction = Mock()
        strategy.start()

        bidder_1 = Mock(reserved_balance=Decimal(10))

        with self.assertRaises(BiddingNotAllowed) as cm:
            strategy.bid(bidder=bidder_1, amount=Decimal(4))
        self.assertEqual(cm.exception.reason, BiddingErrorReason.InsufficientAmount)

        strategy.stop()

    def test_bid_bidder_has_insufficient_balance(self):
        strategy = IncrementBiddingStrategy(initial_price=Decimal(3.00))
        strategy.auction = Mock()
        strategy.start()
        bidder_1 = RuntimeUser(
            username="BillieJean",
            email="lover@michaeljackson.org",
            password_raw="the kid is micheal's son",
            first_name="Billie",
            last_name="Jean",
        )

        bidder_1.initial_balance = 10

        with self.assertRaises(InsufficientBalanceError):
            strategy.bid(bidder=bidder_1, amount=Decimal(20))

        strategy.stop()

    def test_get_current_winner_and_amount(self):
        strategy = IncrementBiddingStrategy(initial_price=Decimal(3.00))
        strategy.auction = Mock()
        strategy.start()
        self.assertEqual((None, None), strategy.get_current_winner_and_amount())

        bidder_1 = RuntimeUser(
            username="Lover",
            email="lover@michaeljackson.org",
            password_raw="the kid is micheal's son",
            first_name="Billie",
            last_name="Jean",
        )
        bidder_2 = RuntimeUser(
            username="JustAGirl",
            email="justagirl@michaeljackson.org",
            password_raw="the kid is not my son",
            first_name="Billie",
            last_name="Jean",
        )

        bidder_1.persistent_user = Mock(id=1)
        bidder_2.persistent_user = Mock(id=2)
        bidder_1.initial_balance = 10
        bidder_2.initial_balance = 20

        self.assertEqual(Decimal(3), strategy.get_current_price())

        strategy.bid(bidder=bidder_1, amount=Decimal(4))
        strategy.bid(bidder=bidder_2, amount=Decimal(5))
        self.assertEqual(Decimal(5), strategy.get_current_price())

        strategy.bid(bidder=bidder_1, amount=Decimal(6))
        strategy.stop()

        self.assertEqual(
            (bidder_1, Decimal(6)), strategy.get_current_winner_and_amount()
        )


class DecrementBiddingStrategyTestCase(TestCase):
    def test_get_current_winner(self):
        tick_ms = 10
        strategy = DecrementBiddingStrategy(initial_price=Decimal(5), tick_ms=tick_ms)
        strategy.auction = Mock()
        strategy.start()
        bidder_1 = Mock(reserved_balance=Decimal(10))
        sleep(23 / 1000)
        strategy.bid(bidder_1)
        strategy.stop()

        self.assertEqual(
            strategy.get_current_winner_and_amount(), (bidder_1, Decimal(3))
        )

    def test_get_current_price_at_different_samples(self):
        tick_ms = 10
        half_tick_ms = tick_ms / 2
        strategy = DecrementBiddingStrategy(initial_price=Decimal(5), tick_ms=tick_ms)
        strategy.auction = Mock()
        strategy.start()

        price_samples = set()

        while len(price_samples) < 5:
            price_samples.add(strategy.get_current_price())
            sleep(half_tick_ms / 1000)

        self.assertLessEqual(
            {Decimal(5), Decimal(4), Decimal(3), Decimal(2), Decimal(1)}, price_samples
        )

        strategy.stop()


class HighestContributionBiddingStrategyTestCase(TestCase):
    def test_bid_less_than_minimum_bid_amount_fails(self):
        strategy = HighestContributionBiddingStrategy(minimum_bid_amount=Decimal(5))
        strategy.auction = Mock()
        strategy.start()

        bidder_1 = Mock(reserved_balance=Decimal(10))

        with self.assertRaises(BiddingNotAllowed) as cm:
            strategy.bid(bidder=bidder_1, amount=Decimal(4))
        self.assertEqual(cm.exception.reason, BiddingErrorReason.InsufficientAmount)

        strategy.stop()

    def test_bid_higher_than_maximum_price_fails(self):
        strategy = HighestContributionBiddingStrategy(
            minimum_bid_amount=Decimal(5), maximum_price=Decimal(100)
        )
        strategy.auction = Mock()
        strategy.start()

        bidder_1 = RuntimeUser(
            username="Lover",
            email="lover@michaeljackson.org",
            password_raw="the kid is micheal's son",
            first_name="Billie",
            last_name="Jean",
        )
        bidder_2 = RuntimeUser(
            username="JustAGirl",
            email="justagirl@michaeljackson.org",
            password_raw="the kid is not my son",
            first_name="Billie",
            last_name="Jean",
        )

        bidder_1.persistent_user = Mock(id=1)
        bidder_2.persistent_user = Mock(id=2)
        bidder_1.initial_balance = 60
        bidder_2.initial_balance = 60

        strategy.bid(bidder=bidder_1, amount=Decimal(40))
        strategy.bid(bidder=bidder_2, amount=Decimal(40))
        with self.assertRaises(InsufficientBalanceError):
            strategy.bid(bidder=bidder_2, amount=Decimal(40))

    def test_get_current_winner_and_amount(self):
        strategy = HighestContributionBiddingStrategy(
            minimum_bid_amount=Decimal(5), maximum_price=Decimal(150)
        )
        strategy.auction = Mock()
        strategy.start()

        bidder_1 = RuntimeUser(
            username="Lover",
            email="lover@michaeljackson.org",
            password_raw="the kid is micheal's son",
            first_name="Billie",
            last_name="Jean",
        )
        bidder_2 = RuntimeUser(
            username="JustAGirl",
            email="justagirl@michaeljackson.org",
            password_raw="the kid is not my son",
            first_name="Billie",
            last_name="Jean",
        )

        bidder_1.persistent_user = Mock(id=1)
        bidder_2.persistent_user = Mock(id=2)
        bidder_1.initial_balance = 60
        bidder_2.initial_balance = 60

        self.assertEqual(strategy.get_current_winner_and_amount(), (None, None))
        self.assertEqual(strategy.get_current_price(), Decimal(0))

        strategy.bid(bidder=bidder_1, amount=Decimal(40))
        self.assertEqual(
            strategy.get_current_winner_and_amount(), (bidder_1, Decimal(40))
        )

        strategy.bid(bidder=bidder_1, amount=Decimal(20))
        self.assertEqual(
            strategy.get_current_winner_and_amount(), (bidder_1, Decimal(60))
        )

        strategy.bid(bidder=bidder_2, amount=Decimal(50))
        self.assertEqual(
            strategy.get_current_winner_and_amount(), (bidder_1, Decimal(60))
        )
