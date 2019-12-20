import asyncio
import threading

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.generic.base import TemplateView, View

from bidpazari.core.forms import (
    AddBalanceForm,
    CreateAuctionStep1Form,
    CreateDecrementAuctionForm,
    CreateHighestContributionAuctionForm,
    CreateIncrementAuctionForm,
    ItemForm,
    SignupForm,
)
from bidpazari.core.models import Item, UserHasItem
from bidpazari.core.runtime.common import runtime_manager


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
        runtime_user = request.user.runtime_user

        return render(
            request, 'core/dashboard.html', {'items': runtime_user.list_items()}
        )


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
                messages.INFO,
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
                request, messages.INFO, f'Successfully edited {instance.title}.'
            )
            return redirect(reverse('dashboard'))

        return render(request, 'core/edit_item.html', {'item': instance, 'form': form})


class AddBalanceView(View):
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
            messages.add_message(request, messages.INFO, message)

            return redirect(reverse('dashboard'))

        return render(request, 'core/add_balance.html', {'form': form})


class CreateAuctionStep1View(View):
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


class CreateAuctionStep2View(View):
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
            runtime_manager.create_auction(
                uhi=uhi,
                bidding_strategy_identifier=bidding_strategy,
                **form.cleaned_data,
            )
            messages.add_message(request, messages.INFO, 'Auction has been created.')
            return redirect(reverse('dashboard'))

        return render(
            request,
            'core/create_auction_confirm.html',
            {'form': form, 'bidding_strategy': bidding_strategy, 'item': item},
        )
