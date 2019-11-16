from time import sleep
from unittest import skip

from django.test import TestCase

from bidpazari.core.exceptions import BiddingErrorReason, BiddingNotAllowed
from bidpazari.core.runtime import (DecrementBiddingStrategy,
                                    HighestContributionBiddingStrategy,
                                    IncrementBiddingStrategy)


@skip('Needs updating')
class IncrementBiddingStrategyTestCase(TestCase):
    def test_bid_success(self):
        strategy = IncrementBiddingStrategy(initial_price=3.00)
        strategy.start()
        strategy.bid(bidder=123, amount=5.00)
        strategy.stop()

        self.assertIn((123, 5.00), strategy.bidding_history)
        self.assertEqual(strategy.highest_bid, 5.00)
        self.assertEqual(strategy.highest_bidder, 123)

    def test_bid_lower_than_highest_amount_fails(self):
        strategy = IncrementBiddingStrategy(initial_price=0.00)
        strategy.start()
        strategy.bid(bidder=123, amount=5.00)

        with self.assertRaises(BiddingNotAllowed) as cm:
            strategy.bid(bidder=456, amount=4.00)
        self.assertEqual(cm.exception.reason, BiddingErrorReason.InsufficientAmount)

        strategy.stop()

    def test_bid_incrementing_less_than_allowed_amount_fails(self):
        strategy = IncrementBiddingStrategy(initial_price=1.00,
                                            minimum_increment=1.0)
        strategy.start()
        strategy.bid(bidder=123, amount=5.00)

        with self.assertRaises(BiddingNotAllowed) as cm:
            strategy.bid(bidder=456, amount=5.50)
        self.assertEqual(cm.exception.reason, BiddingErrorReason.InsufficientAmount)

        strategy.stop()

    def test_bid_incrementing_higher_than_maximum_amount_fails(self):
        strategy = IncrementBiddingStrategy(initial_price=20.0,
                                            maximum_price=50.0)
        strategy.start()
        strategy.bid(bidder=123, amount=40.00)

        with self.assertRaises(BiddingNotAllowed) as cm:
            strategy.bid(bidder=456, amount=60.0)
        self.assertEqual(cm.exception.reason, BiddingErrorReason.AmountTooHigh)

        strategy.stop()

    def test_get_current_winner(self):
        strategy = IncrementBiddingStrategy(initial_price=20.0)
        self.assertIsNone(strategy.get_current_winner())

        strategy.start()
        strategy.bid(bidder=123, amount=25.00)
        self.assertEqual(strategy.get_current_winner(), 123)

        strategy.bid(bidder=456, amount=27.00)
        self.assertEqual(strategy.get_current_winner(), 456)

        strategy.stop()

    def test_get_current_price(self):
        strategy = IncrementBiddingStrategy(initial_price=20.0)
        self.assertEqual(strategy.get_current_price(), 20.0)

        strategy.start()
        strategy.bid(bidder=123, amount=25.00)
        self.assertEqual(strategy.get_current_price(), 25.00)

        strategy.bid(bidder=456, amount=27.00)
        self.assertEqual(strategy.get_current_price(), 27.00)

        strategy.stop()


@skip('Needs updating')
class DecrementBiddingStrategyTestCase(TestCase):
    def test_get_current_winner(self):
        tick_ms = 10
        strategy = DecrementBiddingStrategy(initial_price=5.00, tick_ms=tick_ms)
        strategy.start()
        strategy.bid(123)

        self.assertEqual(strategy.get_current_winner(), 123)

        strategy.stop()

    def test_get_current_price_at_different_samples(self):
        tick_ms = 10
        half_tick_ms = tick_ms / 2
        strategy = DecrementBiddingStrategy(initial_price=5.00, tick_ms=tick_ms)
        strategy.start()

        price_samples = set()

        while len(price_samples) < 5:
            price_samples.add(strategy.get_current_price())
            sleep(half_tick_ms / 1000)

        self.assertLessEqual({5.00, 4.00, 3.00, 2.00, 1.00}, price_samples)

        strategy.stop()


@skip('Needs updating')
class HighestContributionBiddingStrategyTestCase(TestCase):
    def test_bid_less_than_minimum_bid_amount_fails(self):
        strategy = HighestContributionBiddingStrategy(minimum_bid_amount=5.0)
        strategy.start()

        with self.assertRaises(BiddingNotAllowed) as cm:
            strategy.bid(bidder=123, amount=4.00)
        self.assertEqual(cm.exception.reason, BiddingErrorReason.InsufficientAmount)

        strategy.stop()

    def test_bid_higher_than_maximum_price_fails(self):
        strategy = HighestContributionBiddingStrategy(minimum_bid_amount=5.0,
                                                      maximum_price=100.0)
        strategy.start()

        strategy.bid(bidder=123, amount=40.00)
        strategy.bid(bidder=124, amount=40.00)
        with self.assertRaises(BiddingNotAllowed) as cm:
            strategy.bid(bidder=125, amount=40.00)
        self.assertEqual(cm.exception.reason, BiddingErrorReason.AmountTooHigh)

        strategy.stop()

    def test_get_current_winner(self):
        strategy = HighestContributionBiddingStrategy(minimum_bid_amount=5.0, maximum_price=100.0)
        strategy.start()
        self.assertEqual(strategy.get_current_winner(), None)

        strategy.bid(bidder=123, amount=40.00)
        self.assertEqual(strategy.get_current_winner(), 123)

        strategy.bid(bidder=124, amount=41.00)
        self.assertEqual(strategy.get_current_winner(), 124)

        strategy.stop()

    def test_get_current_price(self):
        strategy = HighestContributionBiddingStrategy(minimum_bid_amount=5.0, maximum_price=100.0)
        strategy.start()
        self.assertEqual(strategy.get_current_price(), 0.0)

        strategy.bid(bidder=123, amount=40.00)
        self.assertEqual(strategy.get_current_price(), 40.00)

        strategy.bid(bidder=124, amount=41.00)
        self.assertEqual(strategy.get_current_price(), 81.00)

        strategy.stop()
