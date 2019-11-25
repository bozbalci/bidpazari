from django.core.management import BaseCommand

from bidpazari.core.runtime.net import start_pazar


class Command(BaseCommand):
    def handle(self, *args, **options):
        start_pazar()
