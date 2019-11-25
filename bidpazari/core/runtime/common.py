from bidpazari.core.models import UserHasItem


class RuntimeManager:
    def __init__(self):
        self.active_auctions = {}
        self.item_watchers = []
        self.online_users = set()

    def create_auction(
        self, uhi: UserHasItem, bidding_strategy_identifier: str, **kwargs
    ):
        from bidpazari.core.runtime.auction import Auction

        auction = Auction(
            uhi=uhi, bidding_strategy_identifier=bidding_strategy_identifier, **kwargs
        )
        self.active_auctions[uhi.id] = auction
        self.notify_users_of_new_auction(auction)
        return auction

    def notify_users_of_new_auction(self, auction):
        for item_watcher in self.item_watchers:
            item_watcher.notify(auction.item, auction.initial_price)

    def register_item_watcher(self, item_watcher):
        self.item_watchers.append(item_watcher)


runtime_manager = RuntimeManager()
