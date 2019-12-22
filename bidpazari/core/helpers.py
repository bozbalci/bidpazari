import json

from django.core import serializers
from django.http import Http404

from bidpazari.core.models import User
from bidpazari.core.templatetags.core.tags import money


def verify_user(email, verification_number):
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        raise Exception("No user with this email exists.")

    if user.verification_number == verification_number:
        user.verify()
    else:
        user.email_user()


def get_auction_or_404(pk):
    from bidpazari.core.runtime.common import runtime_manager

    try:
        return runtime_manager.auctions[pk]
    except KeyError:
        raise Http404("Auction not found.")


def serialize_user(user: User, fields=None):
    if fields is None:
        fields = ("id", "first_name", "last_name")
    data_str = serializers.serialize("json", [user], fields=fields)
    data = json.loads(data_str)
    return data[0]["fields"]


def get_human_readable_activity_message(activity):
    data = activity["data"]
    activity_type = activity["type"]

    if activity_type == "auction_stopped":
        winner = data["winner"]
        amount = data["amount"]

        if winner:
            winner_name = f"{winner['first_name']} {winner['last_name']}"
            amount_money = money(amount)
            msg = f"Auction stopped. {winner_name} won with {amount_money}."
        else:
            msg = f"Auction stopped. Nobody won."
        return msg
    elif activity_type == "auction_started":
        current_price = data["current_price"]
        current_price_money = money(current_price)
        return f"Auction started. Current price is {current_price_money}."
    elif activity_type == "bid_received":
        bidder = data["bidder"]
        amount = data["amount"]
        bidder_name = f"{bidder['first_name']} {bidder['last_name']}"
        amount_money = money(amount)
        return f"{bidder_name} made a bid: {amount_money}."
    elif activity_type == "price_decremented":
        current_price = data["current_price"]
        current_price_money = money(current_price)
        return f"Price decremented to {current_price_money}."

    return ""
