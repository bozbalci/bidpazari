import asyncio
import threading

from django.contrib import messages
from django.contrib.auth import logout
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


class LegacyView(TemplateView):
    template_name = 'core/index.html'


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        runtime_user = request.user.runtime_user
        runtime_user.disconnect()
        logout(request)
        messages.add_message(request, messages.INFO, 'You have logged out.')
        return redirect(reverse('legacy-index'))


class DashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        runtime_user = request.user.runtime_user

        context = {'items': runtime_user.list_items()}

        return render(request, 'core/legacy/dashboard.html', context)


class AddItemView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        context = {'form': ItemForm()}

        return render(request, 'core/legacy/add_item.html', context)

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
            return redirect(reverse('legacy-dashboard'))


class EditItemView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        item = get_object_or_404(Item, pk=pk)

        context = {
            'item': item,
            'form': ItemForm(instance=item),
        }

        return render(request, 'core/legacy/edit_item.html', context)

    def post(self, request, *args, **kwargs):
        pk = kwargs['pk']
        instance = get_object_or_404(Item, pk=pk)
        form = ItemForm(request.POST, request.FILES, instance=instance)

        if form.is_valid():
            instance = form.save()
            messages.add_message(
                request, messages.INFO, f'Successfully edited {instance.title}.'
            )
            return redirect(reverse('legacy-dashboard'))


class AddBalanceView(View):
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

            return redirect(reverse('legacy-dashboard'))

    def get(self, request, *args, **kwargs):
        return render(
            request, 'core/legacy/add_balance.html', context={'form': AddBalanceForm()}
        )


class CreateAuctionStep1View(View):
    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        item = get_object_or_404(Item, pk=pk)

        context = {
            'item': item,
            'form': CreateAuctionStep1Form(),
        }

        return render(request, 'core/legacy/create_auction.html', context)

    def post(self, request, *args, **kwargs):
        pk = kwargs['pk']
        item = get_object_or_404(Item, pk=pk)

        form = CreateAuctionStep1Form(request.POST)

        if form.is_valid():
            bidding_strategy = form.cleaned_data['bidding_strategy']
            response = redirect(
                reverse('legacy-create-auction-confirm', kwargs={'pk': item.id})
            )
            response['Location'] += '?' + urlencode(
                {'bidding_strategy': bidding_strategy}
            )
            return response


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

        return render(request, 'core/legacy/create_auction_confirm.html', context)

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
            return redirect(reverse('legacy-dashboard'))
