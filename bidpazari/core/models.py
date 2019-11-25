import random
import string
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum

from bidpazari.core.exceptions import InvalidPassword, UserVerificationError
from bidpazari.core.managers import ItemQuerySet, UserHasItemQuerySet


def generate_verification_number():
    return str(random.randint(100000, 999999))


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(TimeStampedModel, AbstractUser):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    VERIFICATION_STATUS = [(VERIFIED, "Verified"), (UNVERIFIED, "Unverified")]

    verification_status = models.CharField(
        max_length=16, choices=VERIFICATION_STATUS, default=UNVERIFIED
    )
    verification_number = models.CharField(
        max_length=16, default=generate_verification_number, blank=True
    )

    def verify(self, verification_number):
        if self.verification_number == verification_number:
            self.verification_status = User.VERIFIED
            self.save()
            self.email_user(
                subject="Your account was verified.",
                message="Welcome to Bidpazari! Your account is now verified.",
            )
        else:
            raise UserVerificationError("Invalid verification number.")

    def change_password(self, new_password, old_password=None):
        forgotten = old_password is None

        if forgotten:
            letters = string.ascii_letters + string.digits + string.punctuation
            raw_password = "".join(random.choice(letters) for i in range(16))
            self.set_password(raw_password)
            self.email_user(
                subject="Your password was reset",
                message=f"Here is your new password: {raw_password}",
            )
            self.save()
            return raw_password
        elif self.check_password(old_password):
            self.set_password(new_password)
            self.save()
            self.email_user(
                subject="Your password was changed",
                message="Your password was changed.",
            )
            return new_password
        else:
            raise InvalidPassword("The password you entered was incorrect.")

    def list_items(self, item_type=None, on_sale=None):
        item_ids = (
            UserHasItem.objects.filter_by_user(self)
            .filter_by_item_type(item_type)
            .filter_by_on_sale(on_sale)
            .values_list("item", flat=True)
        )

        return Item.objects.filter(id__in=item_ids)

    @property
    def balance(self):
        incoming_transactions_sum = self.incoming_transactions.aggregate(Sum("amount"))[
            "amount__sum"
        ]
        outgoing_transactions_sum = self.outgoing_transactions.aggregate(Sum("amount"))[
            "amount__sum"
        ]

        if incoming_transactions_sum is None:
            incoming_transactions_sum = Decimal(0)
        if outgoing_transactions_sum is None:
            outgoing_transactions_sum = Decimal(0)

        return incoming_transactions_sum - outgoing_transactions_sum

    def add_balance(self, amount):
        """
        Updates the user's balance by creating a new transaction.

        :param amount: Amount in dollars, may be negative.
        """
        Transaction.objects.create(
            amount=amount, source=None, destination=self, item=None
        )

    @property
    def transaction_history(self):
        items_on_sale = "\n".join(map(str, self.list_items(on_sale=True)))

        all_transactions = (
            self.outgoing_transactions.all() | self.incoming_transactions.all()
        ).order_by("id")
        transactions = "\n".join(map(str, all_transactions))

        return f"""\
Transaction History for {self.get_full_name()} (User #{self.id})
Your Balance: {self.balance}


Your Items On Sale
==================
{items_on_sale}


Your Transaction History
========================
{transactions}
"""


class Item(TimeStampedModel):
    title = models.CharField(max_length=128)
    description = models.CharField(max_length=128, blank=True)
    item_type = models.CharField(max_length=128, blank=True)
    on_sale = models.BooleanField(default=False)
    image = models.ImageField(upload_to="images/%Y-%m/", blank=True)

    objects = ItemQuerySet.as_manager()

    def __str__(self):
        return f"Item #{self.id} - {self.title}"


class Transaction(TimeStampedModel):
    amount = models.DecimalField(max_digits=7, decimal_places=2, blank=False)
    source = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="outgoing_transactions",
        blank=True,
        null=True,
    )
    destination = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="incoming_transactions",
        blank=False,
        null=True,
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="transactions",
        blank=True,
        null=True,
    )

    def __str__(self):
        if self.source is None:
            word = "Deposit" if self.amount > 0 else "Withdrawal"
            return f"{word} #{self.id} - Amount: ${self.amount} - Time: {self.created}"

        return (
            f"Transaction #{self.id} - Amount: ${self.amount} - "
            f"From: #{self.source.id} - To: #{self.destination.id} - "
            f"Time: {self.created}"
        )


class UserHasItem(TimeStampedModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_has_items", blank=False
    )
    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="item_has_users", blank=False
    )
    is_sold = models.BooleanField(default=False)

    objects = UserHasItemQuerySet.as_manager()
