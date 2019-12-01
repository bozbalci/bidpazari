from django.core.management import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--web', action='store_true', help='Run WebSockets server')

    def handle(self, *args, **options):
        if options['web']:
            from bidpazari.core.runtime.net.ws import start_pazar_ws

            start_pazar_ws()
        else:
            from bidpazari.core.runtime.net.tcp import start_pazar_tcp

            start_pazar_tcp()
