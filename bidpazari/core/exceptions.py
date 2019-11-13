from enum import Enum


class BiddingErrorReason(Enum):
    InsufficientAmount = (
        'You must bid a higher amount!'
    )

    AmountTooHigh = (
        'Your bidding amount is too high!'
    )


class BiddingNotAllowed(Exception):

    def __init__(self, reason=None):
        self.reason = reason
