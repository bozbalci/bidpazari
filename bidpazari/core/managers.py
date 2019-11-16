from django.db import models


class ItemQuerySet(models.QuerySet):
    def filter_by_item_type(self, item_type):
        if item_type is None:
            return self.all()
        return self.filter(item_type=item_type)

    def filter_by_on_sale(self, on_sale):
        if on_sale is None:
            return self.all()
        return self.filter(on_sale=on_sale)


class UserHasItemQuerySet(models.QuerySet):
    def filter_by_user(self, user):
        return self.filter(user=user)

    def filter_by_item_type(self, item_type):
        if item_type is None:
            return self.all()
        return self.filter(item__item_type=item_type)

    def filter_by_on_sale(self, on_sale):
        if on_sale is None:
            return self.all()
        return self.filter(item__on_sale=on_sale)
