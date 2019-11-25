from decimal import Decimal
from time import sleep
from unittest import skip
from unittest.mock import Mock, call, patch

from django.test import TestCase, override_settings

from bidpazari.core.exceptions import (
    BiddingErrorReason,
    BiddingNotAllowed,
    InsufficientBalanceError,
    InvalidPassword,
    UserVerificationError,
)
from bidpazari.core.models import Item, Transaction, User, UserHasItem
from bidpazari.core.runtime.common import runtime_manager
from bidpazari.core.runtime.user import RuntimeUser


@override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
class UserTestCase(TestCase):
    def test_all(self):
        user = RuntimeUser(
            username="BillieJean",
            email="lover@michaeljackson.org",
            password_raw="the kid is micheal's son",
            first_name="Billie",
            last_name="Jean",
        )
        user.persist()

        # Test verification number and verification flows
        actual_verification_number = user.persistent_user.verification_number
        self.assertEqual(user.persistent_user.verification_status, User.UNVERIFIED)
        with self.assertRaises(UserVerificationError):
            user.verify("this is obviously not the correct validation number")
        self.assertEqual(user.persistent_user.verification_status, User.UNVERIFIED)
        user.verify(actual_verification_number)
        self.assertEqual(user.persistent_user.verification_status, User.VERIFIED)

        # Test password change flows
        with self.assertRaises(InvalidPassword):
            user.change_password(
                new_password="you got hacked kiddo",
                old_password="psych! you actually didn't :)",
            )
        newly_generated_password = user.change_password(
            new_password=None, old_password=None
        )
        self.assertEqual(len(newly_generated_password), 16)
        user.change_password(
            new_password="*********************", old_password=newly_generated_password
        )

        # Test item listing scenarios
        pencil = Item.objects.create(title="Pencil", item_type="Stationary")
        notepad = Item.objects.create(title="Notepad", item_type="Stationary")
        coffee_mug = Item.objects.create(title="Coffee Mug", item_type="Kitchen")
        towel = Item.objects.create(title="Towel", item_type="Kitchen", on_sale=True)
        watch = Item.objects.create(title="Watch", item_type="Accessory", on_sale=True)
        items = [pencil, notepad, coffee_mug, towel, watch]

        for item in items:
            UserHasItem.objects.create(
                user=user.persistent_user, item=item, is_sold=False
            )

        self.assertSetEqual(
            user.list_items(), {pencil, notepad, coffee_mug, towel, watch}
        )
        self.assertSetEqual(user.list_items(on_sale=True), {towel, watch})
        self.assertSetEqual(
            user.list_items(on_sale=False), {pencil, notepad, coffee_mug}
        )
        self.assertSetEqual(user.list_items(item_type="Kitchen"), {coffee_mug, towel})
        self.assertSetEqual(user.list_items(item_type="Kitchen", on_sale=True), {towel})

        # Test balance
        user.add_balance_transaction(Decimal(30.00))
        self.assertEqual(user.initial_balance, Decimal(30.00))
        user.add_balance_transaction(Decimal(-5.00))
        self.assertEqual(user.initial_balance, Decimal(25.00))

        # Test transaction history
        john = RuntimeUser(
            username="john1144",
            email="john1144@fbdymail.com",
            password_raw="11441144",
            first_name="John",
            last_name="Sims",
        )
        john.persist()

        # towel and watch are already on sale at this point

        Transaction.objects.create(
            source=user.persistent_user,
            destination=john.persistent_user,
            amount=Decimal(140.00),
            item=notepad,
        )
        Transaction.objects.create(
            source=john.persistent_user,
            destination=user.persistent_user,
            amount=Decimal(230.00),
            item=coffee_mug,
        )

        print(user.transaction_history)

        # Test item watching capabilities
        watcher_method = lambda item_on_auction, starting_price: None
        user.watcher_method = watcher_method

        patcher = patch.object(user, "watcher_method")
        m_user_watcher_method = patcher.start()

        user.register_item_watcher(user.watcher_method, item_type=None)
        auction = Mock(item=Mock(item_type="Furniture"), initial_price=Decimal(10.99))
        runtime_manager.notify_users_of_new_auction(auction)
        m_user_watcher_method.assert_called_once()

        runtime_manager.item_watchers.clear()
        m_user_watcher_method.reset_mock()
        user.register_item_watcher(user.watcher_method, item_type="Vanity")
        auction = Mock(item=Mock(item_type="Vanity"), initial_price=Decimal(10.99))
        runtime_manager.notify_users_of_new_auction(auction)
        m_user_watcher_method.assert_called_once()

        runtime_manager.item_watchers.clear()
        m_user_watcher_method.reset_mock()
        user.register_item_watcher(user.watcher_method, item_type="Kitchen")
        auction = Mock(item=Mock(item_type="Furniture"), initial_price=Decimal(10.99))
        runtime_manager.notify_users_of_new_auction(auction)
        m_user_watcher_method.assert_not_called()

        patcher.stop()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
class BiddingTestCase(TestCase):
    def test_increment_bidding_happy_path(self):
        john = RuntimeUser(
            username="john1144",
            email="john1144@fbdymail.com",
            password_raw="11441144",
            first_name="John",
            last_name="Sims",
        )
        jimmy = RuntimeUser(
            username="jimjamjom",
            email="me@jimjamjom.org",
            password_raw="12345678",
            first_name="James",
            last_name="Hetfield",
        )
        jack = RuntimeUser(
            username="daniels",
            email="me@jackdaniels.com",
            password_raw="i_secretly_like_johnny_walker",
            first_name="Jack",
            last_name="Daniels",
        )

        john.persist()
        jimmy.persist()
        jack.persist()

        john.connect()
        jimmy.connect()
        jack.connect()

        john.add_balance_transaction(Decimal(50.00))
        jimmy.add_balance_transaction(Decimal(40.00))
        jack.add_balance_transaction(Decimal(30.00))

        scarf = Item.objects.create(
            title="Scarf", description="A really cool scarf", item_type="Clothing"
        )
        jimmy_has_scarf = UserHasItem.objects.create(
            item=scarf, user=jimmy.persistent_user
        )

        auction = runtime_manager.create_auction(
            uhi=jimmy_has_scarf,
            bidding_strategy_identifier="increment",
            initial_price=Decimal(5.00),
            minimum_increment=Decimal(2.00),
            maximum_price=None,
        )

        auction.start()
        auction.bid(john, Decimal(20))
        auction.bid(jack, Decimal(23))
        auction.bid(john, Decimal(31))
        auction.sell()

        print(auction.auction_report)
        print(auction.auction_history)

        john.persistent_user.refresh_from_db()
        jimmy.persistent_user.refresh_from_db()
        jack.persistent_user.refresh_from_db()
        jimmy_has_scarf.refresh_from_db()

        john.disconnect()
        jimmy.disconnect()
        jack.disconnect()

        self.assertTrue(jimmy_has_scarf.is_sold)
        self.assertEqual(john.initial_balance, Decimal(19))
        self.assertEqual(jimmy.initial_balance, Decimal(71))
        self.assertEqual(jack.initial_balance, Decimal(30))
        self.assertEqual(john.persistent_user.balance, Decimal(19))
        self.assertEqual(jimmy.persistent_user.balance, Decimal(71))
        self.assertEqual(jack.persistent_user.balance, Decimal(30))

    def test_increment_bidding_exceptions(self):
        john = RuntimeUser(
            username="john1144",
            email="john1144@fbdymail.com",
            password_raw="11441144",
            first_name="John",
            last_name="Sims",
        )
        jimmy = RuntimeUser(
            username="jimjamjom",
            email="me@jimjamjom.org",
            password_raw="12345678",
            first_name="James",
            last_name="Hetfield",
        )
        jack = RuntimeUser(
            username="daniels",
            email="me@jackdaniels.com",
            password_raw="i_secretly_like_johnny_walker",
            first_name="Jack",
            last_name="Daniels",
        )

        john.persist()
        jimmy.persist()
        jack.persist()

        john.connect()
        jimmy.connect()
        jack.connect()

        john.add_balance_transaction(Decimal(50.00))
        jimmy.add_balance_transaction(Decimal(40.00))
        jack.add_balance_transaction(Decimal(30.00))

        scarf = Item.objects.create(
            title="Scarf", description="A really cool scarf", item_type="Clothing"
        )
        jimmy_has_scarf = UserHasItem.objects.create(
            item=scarf, user=jimmy.persistent_user
        )

        auction = runtime_manager.create_auction(
            uhi=jimmy_has_scarf,
            bidding_strategy_identifier="increment",
            initial_price=Decimal(5.00),
            minimum_increment=Decimal(2.00),
            maximum_price=Decimal(15.00),
        )

        # Cannot bid while auction is closed
        with self.assertRaises(BiddingNotAllowed) as cm:
            auction.bid(john, Decimal(123.00))
        self.assertEqual(cm.exception.reason, BiddingErrorReason.AuctionClosed)

        auction.start()

        # Cannot bid in own auction
        with self.assertRaises(BiddingNotAllowed) as cm:
            auction.bid(jimmy, Decimal(1.00))
        self.assertEqual(cm.exception.reason, BiddingErrorReason.OwnAuction)

        # Lower than initial price
        with self.assertRaises(BiddingNotAllowed) as cm:
            auction.bid(john, Decimal(1.00))
        self.assertEqual(cm.exception.reason, BiddingErrorReason.InsufficientAmount)

        # Lower than minimum increment
        with self.assertRaises(BiddingNotAllowed) as cm:
            auction.bid(john, Decimal(6.00))
        self.assertEqual(cm.exception.reason, BiddingErrorReason.InsufficientAmount)

        # Higher than reservable balance
        with self.assertRaises(InsufficientBalanceError):
            auction.bid(john, Decimal(666.00))

        # Happy path
        auction.bid(john, Decimal(7.00))
        self.assertEqual(john.reservable_balance, Decimal(43.00))
        auction.bid(john, Decimal(50.00))  # This closes the auction.
        self.assertEqual(john.reservable_balance, Decimal(0.00))

        print(auction.auction_report)
        print(auction.auction_history)

        # Cannot bid while auction is closed
        with self.assertRaises(BiddingNotAllowed) as cm:
            auction.bid(john, Decimal(123.00))
        self.assertEqual(cm.exception.reason, BiddingErrorReason.AuctionClosed)

        john.persistent_user.refresh_from_db()
        jimmy.persistent_user.refresh_from_db()
        jack.persistent_user.refresh_from_db()
        jimmy_has_scarf.refresh_from_db()

        john.disconnect()
        jimmy.disconnect()
        jack.disconnect()

        self.assertTrue(jimmy_has_scarf.is_sold)
        self.assertEqual(john.initial_balance, Decimal(0))
        self.assertEqual(jimmy.initial_balance, Decimal(90))
        self.assertEqual(jack.initial_balance, Decimal(30))
        self.assertEqual(john.persistent_user.balance, Decimal(0))
        self.assertEqual(jimmy.persistent_user.balance, Decimal(90))
        self.assertEqual(jack.persistent_user.balance, Decimal(30))

    def test_decrement_bidding_and_auction_watching(self):
        john = RuntimeUser(
            username="john1144",
            email="john1144@fbdymail.com",
            password_raw="11441144",
            first_name="John",
            last_name="Sims",
        )
        jimmy = RuntimeUser(
            username="jimjamjom",
            email="me@jimjamjom.org",
            password_raw="12345678",
            first_name="James",
            last_name="Hetfield",
        )

        jimmy.watch_method = lambda *args, **kwargs: None
        patcher = patch.object(jimmy, "watch_method")
        m_jimmy_watch_method = patcher.start()

        john.persist()
        jimmy.persist()

        john.connect()
        jimmy.connect()

        john.add_balance_transaction(Decimal(100.00))
        jimmy.add_balance_transaction(Decimal(40.00))

        scarf = Item.objects.create(
            title="Scarf", description="A really cool scarf", item_type="Clothing"
        )
        jimmy_has_scarf = UserHasItem.objects.create(
            item=scarf, user=jimmy.persistent_user
        )

        auction = runtime_manager.create_auction(
            uhi=jimmy_has_scarf,
            bidding_strategy_identifier="decrement",
            initial_price=Decimal(150.00),
            price_decrement_rate=Decimal(25.00),
            tick_ms=200,
        )

        auction.register_user_to_updates(jimmy.watch_method)  # this is mocked

        auction.start()

        self.assertEqual(auction.bidding_strategy.get_current_price(), Decimal(150.00))
        with self.assertRaises(InsufficientBalanceError):
            auction.bid(
                john
            )  # no amount means that user is bidding to the current price
        sleep(250 / 1000)
        self.assertEqual(auction.bidding_strategy.get_current_price(), Decimal(125.00))
        sleep(250 / 1000)
        self.assertEqual(auction.bidding_strategy.get_current_price(), Decimal(100.00))
        auction.bid(john)  # this terminates the auction

        m_jimmy_watch_method.assert_has_calls(
            [
                call(event_type="auction_started"),
                call(event_type="price_decremented", new_price=Decimal(125.00)),
                call(event_type="price_decremented", new_price=Decimal(100.00)),
                call(event_type="bid_received"),
                # TODO Fix this some day
                call(event_type="price_decremented", new_price=Decimal(75.00)),
                call(event_type="auction_stopped"),
            ]
        )

        print(auction.auction_report)
        print(auction.auction_history)

        john.persistent_user.refresh_from_db()
        jimmy.persistent_user.refresh_from_db()
        jimmy_has_scarf.refresh_from_db()

        john.disconnect()
        jimmy.disconnect()

        self.assertTrue(jimmy_has_scarf.is_sold)
        self.assertEqual(john.initial_balance, Decimal(0))
        self.assertEqual(jimmy.initial_balance, Decimal(140))
        self.assertEqual(john.persistent_user.balance, Decimal(0))
        self.assertEqual(jimmy.persistent_user.balance, Decimal(140))

        patcher.stop()

    @skip("Remove when threading issue is resolved")
    def test_decrement_bidding_with_no_winners(self):
        pass
        john = RuntimeUser(
            username="john1144",
            email="john1144@fbdymail.com",
            password_raw="11441144",
            first_name="John",
            last_name="Sims",
        )
        jimmy = RuntimeUser(
            username="jimjamjom",
            email="me@jimjamjom.org",
            password_raw="12345678",
            first_name="James",
            last_name="Hetfield",
        )

        john.persist()
        jimmy.persist()

        john.connect()
        jimmy.connect()

        john.add_balance_transaction(Decimal(100.00))
        jimmy.add_balance_transaction(Decimal(40.00))

        scarf = Item.objects.create(
            title="Scarf", description="A really cool scarf", item_type="Clothing"
        )
        jimmy_has_scarf = UserHasItem.objects.create(
            item=scarf, user=jimmy.persistent_user
        )

        auction = runtime_manager.create_auction(
            uhi=jimmy_has_scarf,
            bidding_strategy_identifier="decrement",
            initial_price=Decimal(150.00),
            price_decrement_rate=Decimal(50.00),
            tick_ms=20,
        )

        auction.start()

        self.assertEqual(auction.bidding_strategy.get_current_price(), Decimal(150.00))
        sleep(25 / 1000)
        self.assertEqual(auction.bidding_strategy.get_current_price(), Decimal(100.00))
        sleep(25 / 1000)
        self.assertEqual(auction.bidding_strategy.get_current_price(), Decimal(50.00))
        sleep(25 / 1000)
        self.assertEqual(auction.bidding_strategy.get_current_price(), Decimal(0.00))
        sleep(250 / 1000)

        print(auction.auction_report)
        print(auction.auction_history)

        john.persistent_user.refresh_from_db()
        jimmy.persistent_user.refresh_from_db()
        jimmy_has_scarf.refresh_from_db()

        john.disconnect()
        jimmy.disconnect()

        self.assertFalse(jimmy_has_scarf.is_sold)
        self.assertEqual(john.initial_balance, Decimal(100))
        self.assertEqual(jimmy.initial_balance, Decimal(40))
        self.assertEqual(john.persistent_user.balance, Decimal(100))
        self.assertEqual(jimmy.persistent_user.balance, Decimal(40))

    def test_highest_contribution_bidding(self):
        john = RuntimeUser(
            username="john1144",
            email="john1144@fbdymail.com",
            password_raw="11441144",
            first_name="John",
            last_name="Sims",
        )
        jimmy = RuntimeUser(
            username="jimjamjom",
            email="me@jimjamjom.org",
            password_raw="12345678",
            first_name="James",
            last_name="Hetfield",
        )
        jack = RuntimeUser(
            username="daniels",
            email="me@jackdaniels.com",
            password_raw="i_secretly_like_johnny_walker",
            first_name="Jack",
            last_name="Daniels",
        )

        john.persist()
        jimmy.persist()
        jack.persist()

        john.connect()
        jimmy.connect()
        jack.connect()

        john.add_balance_transaction(Decimal(50.00))
        jimmy.add_balance_transaction(Decimal(40.00))
        jack.add_balance_transaction(Decimal(30.00))

        scarf = Item.objects.create(
            title="Scarf", description="A really cool scarf", item_type="Clothing"
        )
        jimmy_has_scarf = UserHasItem.objects.create(
            item=scarf, user=jimmy.persistent_user
        )

        auction = runtime_manager.create_auction(
            uhi=jimmy_has_scarf,
            bidding_strategy_identifier="highest_contribution",
            minimum_bid_amount=Decimal(2.00),
            maximum_price=Decimal(100),
        )

        auction.start()

        # Cannot bid lower than minimum bid amount
        with self.assertRaises(BiddingNotAllowed) as cm:
            auction.bid(jack, Decimal(1.00))
        self.assertEqual(cm.exception.reason, BiddingErrorReason.InsufficientAmount)

        auction.bid(jack, Decimal(2.00))
        auction.bid(john, Decimal(12.00))
        auction.bid(jack, Decimal(11.00))
        auction.sell()

        print(auction.auction_report)
        print(auction.auction_history)

        john.persistent_user.refresh_from_db()
        jimmy.persistent_user.refresh_from_db()
        jack.persistent_user.refresh_from_db()
        jimmy_has_scarf.refresh_from_db()

        john.disconnect()
        jimmy.disconnect()
        jack.disconnect()

        self.assertTrue(jimmy_has_scarf.is_sold)
        self.assertEqual(john.initial_balance, Decimal(38))
        self.assertEqual(jimmy.initial_balance, Decimal(65))
        self.assertEqual(jack.initial_balance, Decimal(17))
        self.assertEqual(john.persistent_user.balance, Decimal(38))
        self.assertEqual(jimmy.persistent_user.balance, Decimal(65))
        self.assertEqual(jack.persistent_user.balance, Decimal(17))

    def test_highest_contribution_bidding_maximum_price(self):
        john = RuntimeUser(
            username="john1144",
            email="john1144@fbdymail.com",
            password_raw="11441144",
            first_name="John",
            last_name="Sims",
        )
        jimmy = RuntimeUser(
            username="jimjamjom",
            email="me@jimjamjom.org",
            password_raw="12345678",
            first_name="James",
            last_name="Hetfield",
        )
        jack = RuntimeUser(
            username="daniels",
            email="me@jackdaniels.com",
            password_raw="i_secretly_like_johnny_walker",
            first_name="Jack",
            last_name="Daniels",
        )

        john.persist()
        jimmy.persist()
        jack.persist()

        john.connect()
        jimmy.connect()
        jack.connect()

        john.add_balance_transaction(Decimal(150.00))
        jimmy.add_balance_transaction(Decimal(140.00))
        jack.add_balance_transaction(Decimal(130.00))

        scarf = Item.objects.create(
            title="Scarf", description="A really cool scarf", item_type="Clothing"
        )
        jimmy_has_scarf = UserHasItem.objects.create(
            item=scarf, user=jimmy.persistent_user
        )

        auction = runtime_manager.create_auction(
            uhi=jimmy_has_scarf,
            bidding_strategy_identifier="highest_contribution",
            minimum_bid_amount=Decimal(2.00),
            maximum_price=Decimal(100),
        )

        auction.start()

        auction.bid(jack, Decimal(30.00))
        auction.bid(john, Decimal(50.00))
        auction.bid(jack, Decimal(30.00))

        print(auction.auction_report)
        print(auction.auction_history)

        john.persistent_user.refresh_from_db()
        jimmy.persistent_user.refresh_from_db()
        jack.persistent_user.refresh_from_db()
        jimmy_has_scarf.refresh_from_db()

        john.disconnect()
        jimmy.disconnect()
        jack.disconnect()

        self.assertTrue(jimmy_has_scarf.is_sold)
        self.assertEqual(john.initial_balance, Decimal(100))
        self.assertEqual(jimmy.initial_balance, Decimal(250))
        self.assertEqual(jack.initial_balance, Decimal(70))
        self.assertEqual(john.persistent_user.balance, Decimal(100))
        self.assertEqual(jimmy.persistent_user.balance, Decimal(250))
        self.assertEqual(jack.persistent_user.balance, Decimal(70))
