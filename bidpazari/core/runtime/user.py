from decimal import Decimal
from functools import wraps

from django.utils.functional import cached_property

from bidpazari.core.exceptions import InsufficientBalanceError, NonPersistentObjectError
from bidpazari.core.models import User
from bidpazari.core.runtime.common import runtime_manager
from bidpazari.core.runtime.watchers import ItemWatcher


def persistent_user_proxy_method(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        if not self.persistent_user:
            raise NonPersistentObjectError(
                f"{fn.__name__} must be called on a persisted user"
            )
        return fn(self, *args, **kwargs)

    return wrapper


class RuntimeUser:
    def __init__(self, username, email, password_raw, first_name, last_name):
        self.username = username
        self.email = email
        self._password = password_raw
        self.first_name = first_name
        self.last_name = last_name
        self.persistent_user = None
        self.initial_balance = Decimal(0)
        self.reserved_balance = Decimal(0)

    """
    Persistence methods
    """

    def persist(self):
        if self.persistent_user:
            return
        self.persistent_user = User.objects.create_user(
            self.username,
            self.email,
            self._password,
            first_name=self.first_name,
            last_name=self.last_name,
        )

    @classmethod
    def from_persistent_user(cls, user: User):
        runtime_user = cls(
            user.username,
            user.email,
            password_raw=None,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        runtime_user.persistent_user = user
        runtime_user.initial_balance = user.balance
        return runtime_user

    @cached_property
    @persistent_user_proxy_method
    def id(self):
        return self.persistent_user.id

    """
    Proxy methods
    """

    @persistent_user_proxy_method
    def verify(self, verification_number):
        self.persistent_user.verify(verification_number)

    @persistent_user_proxy_method
    def change_password(self, new_password, old_password=None):
        return self.persistent_user.change_password(new_password, old_password)

    @persistent_user_proxy_method
    def list_items(self, item_type=None, on_sale=None):
        return set(self.persistent_user.list_items(item_type, on_sale))

    @persistent_user_proxy_method
    def add_balance_transaction(self, amount):
        self.persistent_user.add_balance(amount)
        self.initial_balance = self.persistent_user.balance

    @property
    @persistent_user_proxy_method
    def transaction_history(self):
        return self.persistent_user.transaction_history

    """
    Runtime specific methods
    """

    @staticmethod
    def register_item_watcher(callback_method, item_type=None):
        item_watcher = ItemWatcher(callback_method, item_type=item_type)
        runtime_manager.register_item_watcher(item_watcher)

    @property
    def reservable_balance(self):
        return self.initial_balance - self.reserved_balance

    def reserve_balance(self, amount):
        if amount > self.reservable_balance:
            raise InsufficientBalanceError("Amount is higher than reservable balance.")
        self.reserved_balance += amount

    def unreserve_balance(self, amount):
        if amount > self.reserved_balance:
            raise InsufficientBalanceError("Amount is higher than reserved balance.")
        self.reserved_balance -= amount

    def unreserve_all(self):
        self.reserved_balance = Decimal(0)

    def connect(self):
        runtime_manager.online_users.add(self)

    def disconnect(self):
        runtime_manager.online_users.remove(self)

    """
    Magic methods
    """

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return isinstance(other, RuntimeUser) and self.id == other.id
