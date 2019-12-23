import subprocess

from django.conf import settings
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        webpack_config = settings.WEBPACK_CONFIG
        subprocess.check_call(
            f'npm run build-{webpack_config}', cwd='./static', shell=True
        )
