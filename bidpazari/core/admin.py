from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Item, Transaction, User, UserHasItem

admin.site.register(User, UserAdmin)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    pass


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    pass


@admin.register(UserHasItem)
class UserHasItemAdmin(admin.ModelAdmin):
    pass
