from typing import Optional

from bidpazari.core.models import User, UserHasItem
from bidpazari.core.runtime.exceptions import AuctionDoesNotExist


class RuntimeManager:
    thread = None

    def __init__(self):
        self.auctions = {}
        self.item_watchers = []
        self.online_users = set()

    def get_user_by_id(self, id_: int) -> Optional['RuntimeUser']:
        for user in self.online_users:
            if user.id == id_:
                return user
        return None

    def get_or_create_runtime_user(self, user: User):
        from bidpazari.core.runtime.user import RuntimeUser

        runtime_user = self.get_user_by_id(user.id)

        if runtime_user is None:
            runtime_user = RuntimeUser.from_persistent_user(user)
            runtime_user.connect()

        return runtime_user

    def get_auction_by_id(self, id_: int):
        try:
            return self.auctions[id_]
        except KeyError as e:
            raise AuctionDoesNotExist(f'Auction with ID {e} does not exist.')

    def create_auction(
        self, uhi: UserHasItem, bidding_strategy_identifier: str, **kwargs
    ) -> 'Auction':
        from bidpazari.core.runtime.auction import Auction

        # TODO if item is already being auctioned, raise an exception here

        auction = Auction(
            uhi=uhi, bidding_strategy_identifier=bidding_strategy_identifier, **kwargs
        )
        self.auctions[uhi.id] = auction
        self.notify_users_of_new_auction(auction)
        return auction

    def notify_users_of_new_auction(self, auction):
        for item_watcher in self.item_watchers:
            item_watcher.notify(auction)

    def register_item_watcher(self, item_watcher):
        self.item_watchers.append(item_watcher)


runtime_manager = RuntimeManager()
