"""
Django settings for medic project.

Phase 8: Environment-variable-driven settings via python-decouple.
All sensitive values are read from environment or .env file.
The project runs with zero .env file present using safe dev defaults:
  - DEBUG=True
  - SQLite database
  - localhost ALLOWED_HOSTS
  - InMemory channel layer (no Redis)
  - No enforced HTTPS
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ─── Security ──────────────────────────────────────────────────────────────────

# SECURITY WARNING: keep the secret key used in production secret!
# Old hardcoded key is retired — generate a new one per deployment.
# See .env.example for the pattern.
SECRET_KEY = config(
    "SECRET_KEY",
    default="django-dev-only-insecure-key-change-in-production-!!!"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,testserver",
    cast=Csv()
)

# ─── Application definition ────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'corsheaders',
    'channels',
    'drf_spectacular',

    'accounts',
    'monitoring',
    'medication',
    'alerts',
    'communication',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # corsheaders must be before CommonMiddleware
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'medic.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'medic.wsgi.application'


# ─── Database ─────────────────────────────────────────────────────────────────
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
# DATABASE_URL overrides to PostgreSQL when set; falls back to SQLite for dev.

import dj_database_url

_DATABASE_URL = config("DATABASE_URL", default="")
if _DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            _DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ─── Password validation ───────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ─── Internationalization ──────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# ─── Static / Media ───────────────────────────────────────────────────────────

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = 'media/'

AUTH_USER_MODEL = 'accounts.User'


# ─── REST Framework ───────────────────────────────────────────────────────────

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'medic.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    # Phase 8: throttling — slow brute-force login attempts, light global default.
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/hour',          # anonymous fallback (schema/docs/health are AllowAny)
        'user': '1000/hour',         # authenticated users (generous; tighten per-view if needed)
        'login': '5/min',            # scoped throttle on /api/token/ to slow brute-force
    },
}


# ─── JWT settings ─────────────────────────────────────────────────────────────

SIMPLE_JWT = {
    # Phase 8: short access token, long refresh, rotate on use
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,  # set True and add simplejwt blacklist app if needed
    'AUTH_HEADER_TYPES': ('Bearer',),
}


# ─── OpenAPI / Spectacular ────────────────────────────────────────────────────

SPECTACULAR_SETTINGS = {
    'TITLE': 'MEDIC API',
    'DESCRIPTION': (
        "## MEDICAL SAFETY NOTICE\n"
        "This system is a prototype clinical decision-support notification tool, NOT a diagnostic system. "
        "Outputs such as risk indicators, vital threshold alerts, and wound analysis are decision-support "
        "heuristics and are NOT clinically validated diagnostic findings. They are designed exclusively to "
        "prompt clinical review by the assigned healthcare team.\n\n"
        "## Timezone & Timestamps\n"
        "All timestamps across the API and database are timezone-aware and localized to Asia/Kolkata (IST).\n\n"
        "## Authorization & Privacy Model\n"
        "All patient-scoped endpoints enforce strict ownership and doctor-patient assignment checks. "
        "To avoid disclosing patient existence or confirming resource records to unauthorized callers, "
        "unauthorized access attempts return HTTP 404 Not Found (rather than 403 Forbidden).\n\n"
        "## Global Authentication\n"
        "All protected endpoints require Bearer JWT authentication via the HTTP Authorization header:\n"
        "`Authorization: Bearer <access_token>`\n\n"
        "- Obtain token pair: `POST /api/token/` with `{\"username\": ..., \"password\": ...}`\n"
        "- Refresh access token: `POST /api/token/refresh/` with `{\"refresh\": ...}`\n\n"
        "## Real-Time WebSocket Channels\n"
        "WebSockets authenticate via JWT passed as a query string parameter (`?token=<jwt_access_token>`). "
        "Connections without valid tokens close with code 4401. Unauthorized role or non-participant connections close with code 4403.\n\n"
        "1. **Doctor Alerts Channel**: `ws/alerts/?token=<token>`\n"
        "   - Target: Authenticated doctors with active DoctorProfile.\n"
        "   - Channel Group: `doctor_<doctor_user_id>_alerts`\n"
        "   - Dispatched events: Vital threshold alerts, medication missed dose alerts, and new patient chat message alerts.\n"
        "   - Payload format:\n"
        "     ```json\n"
        "     {\n"
        "       \"id\": 12,\n"
        "       \"patient_id\": 3,\n"
        "       \"patient_display_name\": \"Jane Doe\",\n"
        "       \"severity\": \"high\",\n"
        "       \"message\": \"High fever detected: 39.5 C\",\n"
        "       \"created_at\": \"2026-03-24T10:00:00+05:30\"\n"
        "     }\n"
        "     ```\n\n"
        "2. **Patient Notifications Channel**: `ws/notifications/?token=<token>`\n"
        "   - Target: Authenticated patients with active PatientProfile.\n"
        "   - Channel Group: `patient_<patient_profile_id>_notifications`\n"
        "   - Dispatched events: Scheduled medication dose reminders and new doctor chat messages.\n"
        "   - Payload format:\n"
        "     ```json\n"
        "     {\n"
        "       \"type\": \"medication_reminder\",\n"
        "       \"dose_id\": 45,\n"
        "       \"medicine_name\": \"Amoxicillin\",\n"
        "       \"dosage\": \"500mg\",\n"
        "       \"scheduled_time\": \"08:00 PM\",\n"
        "       \"message\": \"Time for Amoxicillin (500mg) at 08:00 PM.\",\n"
        "       \"created_at\": \"2026-03-24T19:55:00+05:30\"\n"
        "     }\n"
        "     ```\n\n"
        "3. **Doctor-Patient Chat Channel**: `ws/chat/<conversation_id>/?token=<token>`\n"
        "   - Target: Authenticated doctor or patient participating in the active conversation.\n"
        "   - Channel Group: `chat_<conversation_id>`\n"
        "   - Messages sent/received:\n"
        "     ```json\n"
        "     {\n"
        "       \"id\": 101,\n"
        "       \"conversation_id\": 1,\n"
        "       \"sender_id\": 2,\n"
        "       \"sender_name\": \"Dr. John Smith\",\n"
        "       \"sender_role\": \"doctor\",\n"
        "       \"content\": \"How is your incision healing today?\",\n"
        "       \"is_read\": false,\n"
        "       \"created_at\": \"2026-03-24T10:15:00+05:30\"\n"
        "     }\n"
        "     ```\n\n"
        "## Lovable Frontend Integration Guide\n"
        "- **Base API URL**: `http://<backend-host>:8000/api/`\n"
        "- **Default Headers**: `Authorization: Bearer <access_token>`, `Content-Type: application/json` (except file uploads which use `multipart/form-data`)\n"
        "- **WebSocket Base**: `ws://<backend-host>:8000/` (use `wss://` in production with TLS)\n"
        "- **CORS Notice**: CORS configured in Phase 8. `CORS_ALLOWED_ORIGINS` is env-var-driven. "
        "WebSocket origin validation: `AllowedHostsOriginValidator` — add Lovable domain to `ALLOWED_HOSTS` in production."
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    # NOTE: In development Swagger UI is accessible publicly.
    # Restrict to ['rest_framework.permissions.IsAdminUser'] before deploying to production.
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
}


# ─── CORS (Phase 8) ───────────────────────────────────────────────────────────
# CORS_ALLOWED_ORIGINS defaults to common Lovable/dev origins.
# Override CORS_ALLOWED_ORIGINS in .env with the actual Lovable preview/production domain.
#
# WebSocket origin validation: the ASGI stack uses AllowedHostsOriginValidator.
# Add the Lovable frontend domain to ALLOWED_HOSTS in production so WS connections
# from that origin pass the validator.
# CROSS-ORIGIN TOUCHPOINTS (all require the correct CORS_ALLOWED_ORIGINS to be set):
#   - All /api/* REST endpoints
#   - /health/
#   - /api/schema/, /api/docs/
#   - WebSocket connections via ws:// or wss:// (handled by AllowedHostsOriginValidator)

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000",
    cast=Csv()
)

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000",
    cast=Csv()
)


# ─── Security settings (only enforced when DEBUG=False) ───────────────────────
# These settings are deliberately a no-op in dev (DEBUG=True) so the project
# runs with zero configuration out of the box.

if not DEBUG:
    # Enforce non-empty ALLOWED_HOSTS in production
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['localhost', '127.0.0.1']:
        import warnings
        warnings.warn(
            "ALLOWED_HOSTS appears to be set to dev defaults while DEBUG=False. "
            "Set ALLOWED_HOSTS to your production domain in .env.",
            stacklevel=2
        )

    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"


# ─── Channel layers ───────────────────────────────────────────────────────────

import sys
import os

ASGI_APPLICATION = "medic.asgi.application"

REDIS_URL = config("REDIS_URL", default="")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }


# ─── Structured logging ───────────────────────────────────────────────────────
# Logs authentication failures and unhandled errors to stdout.
# NEVER logs tokens, passwords, or PHI.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "[{asctime}] [{levelname}] [{name}] {message}",
            "style": "{",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "loggers": {
        # Auth failures (from custom exception handler and access helpers)
        "medic.exceptions": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "alerts": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "medication": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Django root logger: errors only in production
        "django": {
            "handlers": ["console"],
            "level": "ERROR" if not DEBUG else "WARNING",
            "propagate": False,
        },
        # Root logger fallback
        "": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}


# ─── Test speed optimisation ──────────────────────────────────────────────────

if 'test' in sys.argv:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]