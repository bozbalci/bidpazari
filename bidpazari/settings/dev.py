from .base import *

DEBUG = True

WEBPACK_CONFIG = 'dev'

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INSTALLED_APPS = ['whitenoise.runserver_nostatic'] + INSTALLED_APPS

MESSAGE_LEVEL = message_constants.DEBUG
