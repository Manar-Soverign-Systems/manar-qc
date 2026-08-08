import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production-12345")
DEBUG = os.environ.get("DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,qcg.manar.pk,staging.qcg.manar.pk").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "qc.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "qc.wsgi.application"
ASGI_APPLICATION = "qc.asgi.application"

if os.environ.get("POSTGRES_PASSWORD"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "manar_qc"),
            "USER": os.environ.get("POSTGRES_USER", "manar"),
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "core.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    }
]

# Auth & Session policy
LOGIN_URL = "/accounts/login/"
SESSION_COOKIE_AGE = 43200  # 12 h idle timeout
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Signing keys
SIGNING_KEY_PATH = os.environ.get("SIGNING_KEY_PATH", "")
TRUSTED_PUBKEY_B64 = os.environ.get("TRUSTED_PUBKEY_B64", "")

# SSO / OIDC Config
SSO_ENABLED = os.environ.get("SSO_ENABLED", "0") == "1"
OIDC_AUTH_URL = os.environ.get("OIDC_AUTH_URL", "")
OIDC_TOKEN_URL = os.environ.get("OIDC_TOKEN_URL", "")
OIDC_JWKS_URL = os.environ.get("OIDC_JWKS_URL", "")
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
OIDC_ROLE_CLAIM = os.environ.get("OIDC_ROLE_CLAIM", "roles")
OIDC_ROLE_MAP = {"admin": "admin", "merch": "merch", "qa": "qa", "auditor": "auditor"}
SELF_HOST_VENDOR = os.environ.get("SELF_HOST_VENDOR", "")
