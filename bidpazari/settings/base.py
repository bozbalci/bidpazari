import os

from django.contrib.messages import constants as message_constants
from django.urls import reverse_lazy

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "m-vfln5vln2rb07o$9%##s%b)%n76-h@)20ekzcd!lgpe(*$!g"

DEBUG = False

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third-party apps
    'webpack_loader',
    'argonauts',
    'crispy_forms',
    # Bidpazari
    "bidpazari.core.apps.CoreConfig",
]

# Order of these classes is important!
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bidpazari.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "bidpazari.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "../db.sqlite3"),
    }
}

# Authentication
AUTH_USER_MODEL = "core.User"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",},
]
LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = reverse_lazy('dashboard')

# Messaging
MESSAGE_TAGS = {
    message_constants.DEBUG: 'secondary',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}

# i18n, l10n, timezones, dates, etc.
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_L10N = False
USE_TZ = True
DATE_FORMAT = "M. j, Y - H:i:s"
DATETIME_FORMAT = "M. j, Y - H:i:s"

LOGGING = {
    "version": 1,
    "handlers": {"console": {"level": "INFO", "class": "logging.StreamHandler",}},
    "loggers": {"": {"handlers": ["console"], "level": "INFO"}},
}

# Static files (JS, CSS, assets) and media (user-uploaded images)
STATIC_URL = "/staticx/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "../static/assets/"),
    os.path.join(BASE_DIR, "../static/build/"),
]
STATIC_BUILD_DIR = os.path.join(BASE_DIR, "../static/build/")
print(STATIC_BUILD_DIR)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, "../media")

# Webpack
WEBPACK_CONFIG = 'prod'
WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': STATIC_BUILD_DIR + 'bidpazari/js/webpack',
        'STATS_FILE': STATIC_BUILD_DIR + 'bidpazari/js/webpack/webpack-stats.json',
    }
}

# Crispy forms
CRISPY_TEMPLATE_PACK = 'bootstrap4'
