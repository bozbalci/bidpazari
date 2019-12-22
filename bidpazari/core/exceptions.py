from enum import Enum


class BiddingErrorReason(Enum):
    InsufficientAmount = "You must bid a higher amount!"
    AuctionClosed = "The auction is closed!"
    OwnAuction = "This is your own auction -- you cannot bid in it!"


class BiddingNotAllowed(Exception):
    def __init__(self, reason=None):
        self.reason = reason

    def __str__(self):
        return f"Bidding not allowed: {self.reason.value}"


class InvalidPassword(Exception):
    pass


class UserVerificationError(Exception):
    pass


class InsufficientBalanceError(Exception):
    pass


class NonPersistentObjectError(Exception):
    pass
