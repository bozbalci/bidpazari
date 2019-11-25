from django.db.models.signals import post_save
from django.dispatch import receiver

from bidpazari.core.models import Transaction, User
from bidpazari.core.runtime.common import runtime_manager


@receiver(post_save, sender=Transaction, dispatch_uid="update_balances_of_runtime_users")
def update_balances_of_runtime_users(sender, instance: Transaction, **kwargs):
    if not kwargs["created"]:
        return

    source_user = instance.source
    destination_user = instance.destination

    for user in runtime_manager.online_users:
        if source_user and user.id == source_user.id:
            user.initial_balance = source_user.balance
        elif user.id == destination_user.id:
            user.initial_balance = destination_user.balance


@receiver(post_save, sender=User, dispatch_uid="send_registration_email")
def send_registration_email(sender, instance: User, **kwargs):
    if not kwargs["created"]:
        return

    instance.email_user(
        subject="Welcome to Bidpazari!",
        message=f"Hello {instance.get_full_name()} and welcome to Bidpazari!\n\n"
        f"Please complete your registration by using this"
        f" verification number: {instance.verification_number}",
    )
