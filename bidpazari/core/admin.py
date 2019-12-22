from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Item, Transaction, User, UserHasItem

admin.site.register(User, UserAdmin)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'item_type', 'description', 'current_owner')

    @staticmethod
    def current_owner(obj):
        uhi = UserHasItem.objects.get(item=obj, is_sold=False)
        return uhi.user


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'source', 'destination', 'item')


@admin.register(UserHasItem)
class UserHasItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'item', 'is_sold')
