class Watcher:
    pass


class ItemWatcher(Watcher):
    def __init__(self, callback_method, item_type=None):
        self.callback_method = callback_method
        self.item_type = item_type

    def notify(self, auction):
        item = auction.item

        if not self.item_type or self.item_type == item.item_type:
            self.callback_method(auction)


class AuctionWatcher(Watcher):
    def __init__(self, callback_method):
        self.callback_method = callback_method

    def notify(self, *args, **kwargs):
        self.callback_method(*args, **kwargs)
