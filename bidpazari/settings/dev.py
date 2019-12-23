from .base import *

DEBUG = True

WEBPACK_CONFIG = 'dev'

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

MESSAGE_LEVEL = message_constants.DEBUG
