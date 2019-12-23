import asyncio
import threading

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.generic.base import TemplateView, View

from bidpazari.core.exceptions import (
    BiddingNotAllowed,
    InsufficientBalanceError,
)
from bidpazari.core.forms import (
    AddBalanceForm,
    AuctionBidForm,
    CreateAuctionStep1Form,
    CreateDecrementAuctionForm,
    CreateHighestContributionAuctionForm,
    CreateIncrementAuctionForm,
    ItemForm,
    SignupForm,
)
from bidpazari.core.helpers import get_auction_or_404, zen
from bidpazari.core.models import Item, Transaction, UserHasItem
from bidpazari.core.runtime.auction import AuctionStatus
from bidpazari.core.runtime.common import runtime_manager
from bidpazari.core.runtime.exceptions import (
    InvalidAuctionStatus,
    ItemAlreadyOnSale,
)
from bidpazari.core.templatetags.core.tags import money


class WSServerView(View):
    def get(self, *args, **kwargs):
        from bidpazari.core.runtime.net.websocket import start_pazar_ws

        if runtime_manager.thread is None:

            def start_pazar_ws_in_new_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                start_pazar_ws()

            runtime_manager.thread = threading.Thread(
                target=start_pazar_ws_in_new_thread
            )
            runtime_manager.thread.start()

        return redirect(reverse('ws-client'))


class WSClientView(TemplateView):
    template_name = 'core/ws_client.html'

    def get_context_data(self, **kwargs):
        return {'props': {'test': 42}}


class IndexView(TemplateView):
    template_name = 'core/index.html'

    def get_context_data(self, **kwargs):
        return {'zen': zen}


class SignupView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'core/signup.html', {'form': SignupForm()})

    def post(self, request, *args, **kwargs):
        form = SignupForm(request.POST)

        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect(reverse('dashboard'))

        return render(request, 'core/signup.html', {'form': form})


class LogoutView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        runtime_user = request.user.runtime_user
        runtime_user.disconnect()
        logout(request)
        messages.add_message(request, messages.INFO, 'You have logged out.')
        return redirect(reverse('index'))


class DashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        items = request.user.list_items()

        for item in items:
            item.current_uhi = UserHasItem.objects.get(item=item, is_sold=False)

        return render(request, 'core/dashboard.html', {'items': items})


class AddItemView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return render(request, 'core/add_item.html', {'form': ItemForm()})

    def post(self, request, *args, **kwargs):
        form = ItemForm(request.POST, request.FILES)

        if form.is_valid():
            instance = form.save()
            UserHasItem.objects.create(user=request.user, item=instance)
            messages.add_message(
                request,
                messages.SUCCESS,
                f'Successfully added {instance.title} to your items.',
            )
            return redirect(reverse('dashboard'))

        return render(request, 'core/add_item.html', {'form': form})


class EditItemView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        item = get_object_or_404(Item, pk=pk)

        return render(
            request,
            'core/edit_item.html',
            {'item': item, 'form': ItemForm(instance=item),},
        )

    def post(self, request, *args, **kwargs):
        pk = kwargs['pk']
        instance = get_object_or_404(Item, pk=pk)
        form = ItemForm(request.POST, request.FILES, instance=instance)

        if form.is_valid():
            instance = form.save()
            messages.add_message(
                request, messages.SUCCESS, f'Successfully edited {instance.title}.'
            )
            return redirect(reverse('dashboard'))

        return render(request, 'core/edit_item.html', {'item': instance, 'form': form})


class AddBalanceView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return render(request, 'core/add_balance.html', {'form': AddBalanceForm()})

    def post(self, request, *args, **kwargs):
        form = AddBalanceForm(request.POST)

        if form.is_valid():
            amount = form.cleaned_data['amount']
            request.user.runtime_user.add_balance_transaction(amount)

            if amount > 0:
                message = f'Added ${amount} to your balance.'
            else:
                message = f'Removed ${-amount} from your balance.'
            messages.add_message(request, messages.SUCCESS, message)

            return redirect(reverse('dashboard'))

        return render(request, 'core/add_balance.html', {'form': form})


class CreateAuctionStep1View(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        item = get_object_or_404(Item, pk=pk)

        return render(
            request,
            'core/create_auction.html',
            {'item': item, 'form': CreateAuctionStep1Form(),},
        )

    def post(self, request, *args, **kwargs):
        pk = kwargs['pk']
        item = get_object_or_404(Item, pk=pk)
        form = CreateAuctionStep1Form(request.POST)

        if form.is_valid():
            bidding_strategy = form.cleaned_data['bidding_strategy']
            response = redirect(
                reverse('create-auction-confirm', kwargs={'pk': item.id})
            )
            response['Location'] += '?' + urlencode(
                {'bidding_strategy': bidding_strategy}
            )
            return response

        return render(
            request, 'core/create_auction.html', {'item': item, 'form': form,}
        )


class CreateAuctionStep2View(LoginRequiredMixin, View):
    FORMS = {
        'increment': CreateIncrementAuctionForm,
        'decrement': CreateDecrementAuctionForm,
        'highest_contribution': CreateHighestContributionAuctionForm,
    }

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        item = get_object_or_404(Item, pk=pk)

        bidding_strategy = request.GET.get(
            'bidding_strategy', 'increment'
        )  # default is increment
        form_class = self.FORMS.get(bidding_strategy, CreateIncrementAuctionForm)
        form = form_class()

        context = {'item': item, 'form': form, 'bidding_strategy': bidding_strategy}

        return render(request, 'core/create_auction_confirm.html', context)

    def post(self, request, *args, **kwargs):
        pk = kwargs['pk']
        item = get_object_or_404(Item, pk=pk)
        uhi = get_object_or_404(
            UserHasItem, item=item, user=request.user, is_sold=False
        )
        bidding_strategy = request.POST.get('bidding_strategy')
        form_class = self.FORMS.get(bidding_strategy, CreateIncrementAuctionForm)
        form = form_class(request.POST)

        if form.is_valid():
            try:
                auction = runtime_manager.create_auction(
                    uhi=uhi,
                    bidding_strategy_identifier=bidding_strategy,
                    **form.cleaned_data,
                )
            except ItemAlreadyOnSale as e:
                messages.add_message(request, messages.ERROR, str(e))
            else:
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    'Created the auction! If the below details look correct to you, hit start and let the games begin!',
                )
                return redirect(reverse('auction-details', kwargs={'pk': auction.id}))

        return render(
            request,
            'core/create_auction_confirm.html',
            {'form': form, 'bidding_strategy': bidding_strategy, 'item': item},
        )


class AuctionsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/auctions.html'

    def get_context_data(self, **kwargs):
        auctions = []
        for id_, auction in runtime_manager.auctions.items():
            if auction.status != AuctionStatus.CLOSED:
                auctions.append(auction.to_django())

        return {'auctions': auctions}


class AuctionDetailsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/auction_details.html'

    def get_context_data(self, **kwargs):
        auction = get_auction_or_404(kwargs['pk'])

        auction_is_initial = auction.status == AuctionStatus.INITIAL
        auction_is_open = auction.status == AuctionStatus.OPEN
        auction_is_closed = auction.status == AuctionStatus.CLOSED
        user_owns_auction = auction.owner == self.request.user
        can_start = auction_is_initial and user_owns_auction
        can_sell = auction_is_open and user_owns_auction
        can_bid = auction_is_open and not user_owns_auction

        bid_form = AuctionBidForm()
        if auction.bidding_strategy_identifier == 'decrement':
            bid_form = None

        return {
            'auction': auction.to_django(),
            'auction_is_initial': auction_is_initial,
            'auction_is_open': auction_is_open,
            'auction_is_closed': auction_is_closed,
            'user_owns_auction': user_owns_auction,
            'can_start': can_start,
            'can_sell': can_sell,
            'can_bid': can_bid,
            'bid_form': bid_form,
        }


class AuctionStartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pk = kwargs['pk']
        auction = get_auction_or_404(pk)

        if auction.owner == request.user:
            try:
                auction.start()
            except InvalidAuctionStatus as e:
                messages.add_message(request, messages.ERROR, str(e))
            else:
                messages.add_message(
                    request, messages.SUCCESS, "The auction has been started!",
                )
        else:
            messages.add_message(
                request,
                messages.ERROR,
                "You must be the owner of the auction to start it!",
            )

        return redirect(reverse('auction-details', kwargs={'pk': pk}))


class AuctionCancelView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pk = kwargs['pk']
        auction = get_auction_or_404(pk)

        if auction.owner == request.user:
            try:
                auction.stop()
            except InvalidAuctionStatus as e:
                messages.add_message(request, messages.ERROR, str(e))
            else:
                messages.add_message(
                    request, messages.INFO, "Auction has been cancelled."
                )
                return redirect(reverse('dashboard'))
        else:
            messages.add_message(
                request,
                messages.ERROR,
                "You must be the owner of the auction to cancel it!",
            )

        return redirect(reverse('auction-details', kwargs={'pk': pk}))


class AuctionSellView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pk = kwargs['pk']
        auction = get_auction_or_404(pk)

        if auction.owner == request.user:
            try:
                auction.sell()
            except InvalidAuctionStatus as e:
                messages.add_message(request, messages.ERROR, str(e))
            else:
                (
                    winner,
                    amount,
                ) = auction.bidding_strategy.get_current_winner_and_amount()
                if winner:
                    winner_user_full_name = winner.persistent_user.get_full_name()
                    amount_money = money(amount)
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        f"Auction closed. Sold to {winner_user_full_name} for {amount_money}.",
                    )
                else:
                    messages.add_message(
                        request, messages.INFO, "Auction closed. Nobody won."
                    )
                return redirect(reverse('dashboard'))
        else:
            messages.add_message(
                request,
                messages.ERROR,
                "You must be the owner of the auction to stop it!",
            )

        return redirect(reverse('auction-details', kwargs={'pk': pk}))


class AuctionBidView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user.runtime_user
        pk = kwargs['pk']
        auction = get_auction_or_404(pk)
        form = AuctionBidForm(request.POST)

        if form.is_valid():
            amount = form.cleaned_data['amount']
            try:
                auction.bid(user, amount)
            except (BiddingNotAllowed, InsufficientBalanceError) as e:
                messages.add_message(request, messages.ERROR, str(e))
        else:
            # Decrement bidding uses the same view, but does not have an "amount" field.
            # This check makes it possible to reuse the same view for decrement bidding.
            if auction.bidding_strategy_identifier == 'decrement':
                try:
                    auction.bid(user)
                except (BiddingNotAllowed, InsufficientBalanceError) as e:
                    messages.add_message(request, messages.ERROR, str(e))
        return redirect(reverse('auction-details', kwargs={'pk': pk}))


class TransactionsView(LoginRequiredMixin, TemplateView):
    template_name = 'core/transactions.html'

    def get_context_data(self, **kwargs):
        user = self.request.user

        purchases = Transaction.objects.filter(
            source=user, item__isnull=False
        ).order_by('-created')
        sales = Transaction.objects.filter(
            destination=user, item__isnull=False
        ).order_by('-created')
        deposits = Transaction.objects.filter(
            source=None, destination=user, amount__gt=0
        ).order_by('-created')
        withdrawals = Transaction.objects.filter(
            source=None, destination=user, amount__lte=0
        ).order_by('-created')

        return {
            'purchases': purchases,
            'sales': sales,
            'deposits': deposits,
            'withdrawals': withdrawals,
        }
