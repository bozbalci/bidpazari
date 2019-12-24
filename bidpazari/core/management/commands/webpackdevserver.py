import subprocess
import sys

from django.conf import settings
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        if not settings.DEBUG:
            sys.stderr.write(
                "webpack-dev-server can only be run in development environments\n"
            )
            return
        subprocess.check_call(f'npm run start', cwd='./static', shell=True)
