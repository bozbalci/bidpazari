import random
import string
from enum import Enum, auto

from bidpazari.core.exceptions import InsufficientBalanceError, InvalidPassword
from bidpazari.core.stubs.comms import send_mail
from bidpazari.core.stubs.persistance import UserRepository

user_repository = UserRepository()


class UserVerificationStatus(Enum):
    UNVERIFIED = auto()
    VERIFIED = auto()


class ItemStatus(Enum):
    ANY = auto()
    ON_HOLD = auto()
    ACTIVE = auto()
    SOLD = auto()


class Item:
    def __init__(self, title, description, item_type, status, image=None):
        self.title = title
        self.description = description
        self.item_type = item_type
        self.status = status
        self.image = image


class User:
    def __init__(self, full_name, email, password):
        self.full_name = full_name
        self.email = email
        self.password = password
        self.verification_status = UserVerificationStatus.UNVERIFIED
        self.verification_number = random.randint(100000, 999999)
        self.balance = 0.0
        self.items = []

        send_mail(recipient=email,
                  subject='Welcome to Bidpazari!',
                  message=f'Hello {self.full_name} and welcome to Bidpazari!\n\n'
                          f'Please complete your registration by using this'
                          f' verification number: {self.verification_number}')
        self.save()

    @staticmethod
    def verify(email, verification_number):
        user = user_repository.find_by_email(email)

        if user.verification_number == verification_number:
            user.verification_status = UserVerificationStatus.VERIFIED
            user.save()
        else:
            send_mail(recipient=email,
                      subject='Welcome to Bidpazari!',
                      message=f'Hello {user.full_name} and welcome to Bidpazari!\n\n'
                              f'Apparently you didn\'t quite understand what we meant'
                              f' in our previous email. Your verification number is:'
                              f' {user.verification_number}')

    def change_password(self, new_password, old_password=None):
        forgotten = old_password is None

        if forgotten:
            letters = string.ascii_letters + string.digits
            self.password = ''.join(random.choice(letters) for i in range(8))
            send_mail(recipient=self.email,
                      subject='Your password was reset',
                      message=f'Your new password is: {self.password}')
            self.save()
        elif self.password == old_password:
            self.password = new_password
            self.save()
            send_mail(recipient=self.email,
                      subject='Your password was reset',
                      message='Someone has recently changed the password of your account.\n'
                              'If this was you, then you can disregard this email.\n'
                              'Otherwise, well... You\'re screwed. Sorry!')
        else:
            raise InvalidPassword

    def list_items(self, item_type=None, status=ItemStatus.ANY):
        def filter_function(item):
            item_type_matches = True
            status_matches = True

            if item_type:
                item_type_matches = item.item_type == item_type
            if status != ItemStatus.ANY:
                status_matches = item.status == status

            return item_type_matches and status_matches

        return list(filter(filter_function, self.items))

    def add_balance(self, amount):
        new_balance = self.balance + amount

        if new_balance < 0:
            raise InsufficientBalanceError

        self.balance = new_balance
        self.save()

    """
    Stub methods. Will be replaced in future phases.
    """
    def save(self):
        user_repository.save(self)
