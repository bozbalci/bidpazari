from django import forms
from django.contrib.auth.forms import UserCreationForm

from bidpazari.core.models import Item, User


class SignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(max_length=254, required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['title', 'item_type', 'description', 'image']


class AddBalanceForm(forms.Form):
    amount = forms.DecimalField(required=True, decimal_places=2)


class CreateAuctionStep1Form(forms.Form):
    bidding_strategy = forms.ChoiceField(
        choices=[
            ('increment', 'Increment'),
            ('decrement', 'Decrement'),
            ('highest_contribution', 'Highest Contribution'),
        ],
        required=True,
    )


class CreateIncrementAuctionForm(forms.Form):
    initial_price = forms.DecimalField(required=True)
    minimum_increment = forms.DecimalField(required=True)
    maximum_price = forms.DecimalField(required=True)


class CreateDecrementAuctionForm(forms.Form):
    initial_price = forms.DecimalField(required=True)
    minimum_price = forms.DecimalField(
        required=True,
        help_text="Auction will automatically stop once this price is reached.",
    )
    price_decrement_rate = forms.DecimalField(required=True)
    tick_ms = forms.IntegerField(
        required=True,
        min_value=1000,
        label='Tick time in milliseconds',
        help_text='Must be greater than 1000.',
    )


class CreateHighestContributionAuctionForm(forms.Form):
    minimum_bid_amount = forms.DecimalField(required=True)
    maximum_price = forms.DecimalField(required=True)


class AuctionBidForm(forms.Form):
    amount = forms.DecimalField(required=True)
