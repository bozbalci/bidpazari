from django.core.management import BaseCommand

from bidpazari.core.runtime.net.websocket import start_pazar_ws


class Command(BaseCommand):
    def handle(self, *args, **options):
        start_pazar_ws()
