import asyncio
import threading

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.generic.base import TemplateView, View

from bidpazari.core.exceptions import (
    BiddingNotAllowed,
    InsufficientBalanceError,
    UserVerificationError,
)
from bidpazari.core.forms import (
    AccountDetailsForm,
    AddBalanceForm,
    AuctionBidForm,
    CreateAuctionStep1Form,
    CreateDecrementAuctionForm,
    CreateHighestContributionAuctionForm,
    CreateIncrementAuctionForm,
    ItemForm,
    PasswordResetForm,
    SignupForm,
)
from bidpazari.core.helpers import get_auction_or_404
from bidpazari.core.models import Item, Transaction, User, UserHasItem
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


class SignupView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'core/signup.html', {'form': SignupForm()})

    def post(self, request, *args, **kwargs):
        form = SignupForm(request.POST)

        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Your registration is almost complete!\n"
                "We've sent you an email with a verification link. Check your inbox!",
            )
            return redirect(reverse('login'))

        return render(request, 'core/signup.html', {'form': form})


class UserVerificationView(View):
    def get(self, request, *args, **kwargs):
        token = request.GET.get('token', '')
        verification_number = request.GET.get('v', '')

        try:
            user = User.objects.get(auth_token=token)
            user.verify(verification_number)
            login(request, user)
            messages.add_message(
                request,
                messages.SUCCESS,
                "Your account is now verified! Enjoy bidding!",
            )
            return redirect(reverse('dashboard'))
        except User.DoesNotExist:
            messages.add_message(request, messages.ERROR, f"User does not exist.")
            return redirect(reverse('index'))
        except UserVerificationError as e:
            messages.add_message(request, messages.ERROR, f"Could not verify user: {e}")
            return redirect(reverse('index'))


class LoginView(DjangoLoginView):
    def form_valid(self, form):
        user = form.get_user()

        if user.verification_status == User.VERIFIED:
            login(self.request, user)
            return HttpResponseRedirect(self.get_success_url())
        else:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Your account has not yet been verified. Check your email!",
            )
            return redirect(reverse('login'))

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('dashboard'))
        return super().get(request, *args, **kwargs)


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


class AccountDetailsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = AccountDetailsForm(user=request.user)

        return render(request, 'core/account_details.html', {'form': form,})

    def post(self, request, *args, **kwargs):
        form = AccountDetailsForm(user=request.user, data=request.POST)

        if form.is_valid():
            form.save()
            messages.add_message(
                request, messages.SUCCESS, "Your personal details have been updated."
            )
            return redirect(reverse('account-details'))

        return render(request, 'core/account_details.html', {'form': form,})


class PasswordResetView(View):
    def get(self, request, *args, **kwargs):
        form = PasswordResetForm()

        return render(request, 'core/reset_password.html', {'form': form,})

    def post(self, request, *args, **kwargs):
        form = PasswordResetForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']

            try:
                user = User.objects.get(email=email)
                # The following call resets password
                user.change_password(new_password=None, old_password=None)
            except User.DoesNotExist:
                pass
            finally:
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "If that user exists, then we've sent a mail with the new password.",
                )
                return redirect(reverse('index'))

        return render(request, 'core/reset_password.html', {'form': form,})


class PasswordChangeView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = PasswordChangeForm(user=request.user)

        return render(request, 'core/change_password.html', {'form': form,})

    def post(self, request, *args, **kwargs):
        user = request.user
        form = PasswordChangeForm(data=request.POST, user=user)

        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.add_message(
                request, messages.SUCCESS, "Your password has been changed."
            )
            return redirect(reverse('account-details'))

        return render(request, 'core/change_password.html', {'form': form})


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
            'auction_live_updates_args': {'auctionId': auction.id,},
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


class MarketplaceView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user_id = request.GET.get('user_id', 'all')
        item_type = request.GET.get('item_type', '')
        status = request.GET.get('status', 'any')

        on_sale = {'any': None, 'on_sale': True, 'not_on_sale': False}.get(status)

        all_users = User.objects.all()

        if user_id == 'all':
            users = all_users
        else:
            users = User.objects.filter(id=user_id)

        users_with_items = {}

        for user in users:
            items = user.list_items(item_type=item_type, on_sale=on_sale)

            if items:
                for item in items:
                    item.current_uhi = UserHasItem.objects.get(item=item, is_sold=False)

                users_with_items[user] = items

        return render(
            request,
            'core/marketplace.html',
            {
                'selected_user_id': str(user_id),
                'selected_item_type': item_type,
                'selected_status': status,
                'all_users': all_users,
                'users_with_items': users_with_items,
            },
        )
