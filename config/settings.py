"""
GymPro DZ - settings.

All secrets come from the `.env` file next to manage.py (see .env.example).
Database: set DATABASE_URL to your Supabase connection string.
If DATABASE_URL is empty, a local SQLite file is used (handy for testing / offline demo).
"""
from pathlib import Path
import os
import secrets

import dj_database_url
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.getenv("GYMPRO_ENV_FILE") or BASE_DIR / ".env")  # hosted mode: one env file per gym


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.getenv("SECRET_KEY") or "dev-only-" + secrets.token_urlsafe(32)
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "gym",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "gym.middleware.LicenseMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "gym.context_processors.gym_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------- Database
# Serverless hosts (Vercel) start many short-lived copies of the app: never keep connections open there,
# otherwise the Supabase pooler hits its client limit and random pages fail with error 500.
SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("SERVERLESS"))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0 if SERVERLESS else 60,
            conn_health_checks=not SERVERLESS,
            ssl_require=env_bool("DB_SSL", True),
        )
    }
    _db = DATABASES["default"]
    if str(_db.get("PORT")) == "6543":  # Supabase "Transaction pooler"
        _db["DISABLE_SERVER_SIDE_CURSORS"] = True
        _db.setdefault("OPTIONS", {})["prepare_threshold"] = None
    _db.setdefault("OPTIONS", {}).setdefault("connect_timeout", 10)
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "local_db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# ---------------------------------------------------------------- Languages
LANGUAGE_CODE = os.getenv("DEFAULT_LANGUAGE", "fr")
LANGUAGES = [
    ("fr", "Français"),
    ("ar", "العربية"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Africa/Algiers"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------- Static & media
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Photos & logo: on Vercel (no permanent disk) they are stored inside the database.
MEDIA_IN_DB = env_bool("MEDIA_IN_DB", SERVERLESS)
STORAGES = {
    "default": {"BACKEND": "gym.storage.DatabaseStorage" if MEDIA_IN_DB else "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))
WHITENOISE_USE_FINDERS = True  # CSS/JS work even if collectstatic was not run (e.g. on Vercel)
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024  # webcam photos are sent as text

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
SESSION_COOKIE_AGE = 60 * 60 * 12  # 12h shift

# Online (hosted) mode behind nginx + HTTPS: set HTTPS_PROXY_MODE=true in .env
if env_bool("HTTPS_PROXY_MODE", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    USE_X_FORWARDED_HOST = True

TRIAL_DAYS = 14  # free trial before a license key is required (see gym/license.py)

LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
