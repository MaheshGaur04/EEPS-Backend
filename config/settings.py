"""Django settings for Earth Energy."""

from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv('DEBUG', 'False').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]


def _production_secret(name):
    value = os.getenv(name, '').strip()
    if len(value) < 32 or value.lower().startswith(('change-me', 'django-insecure-', 'your_')):
        raise ImproperlyConfigured(
            f'{name} must be set to a unique, randomly generated secret of at least 32 characters when DEBUG is False.'
        )
    return value


if DEBUG:
    SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-only-change-me')
    ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET', SECRET_KEY)
    REFRESH_TOKEN_SECRET = os.getenv('REFRESH_TOKEN_SECRET', SECRET_KEY)
else:
    SECRET_KEY = _production_secret('SECRET_KEY')
    ACCESS_TOKEN_SECRET = _production_secret('ACCESS_TOKEN_SECRET')
    REFRESH_TOKEN_SECRET = _production_secret('REFRESH_TOKEN_SECRET')
    if len({SECRET_KEY, ACCESS_TOKEN_SECRET, REFRESH_TOKEN_SECRET}) != 3:
        raise ImproperlyConfigured(
            'SECRET_KEY, ACCESS_TOKEN_SECRET, and REFRESH_TOKEN_SECRET must be different values.'
        )
    if not os.getenv('ALLOWED_HOSTS', '').strip() or not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            'Set ALLOWED_HOSTS to the explicit production hostnames when DEBUG is False.'
        )

FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'accounts',
    'contacts',
    'service_requests',
    'roi',
    'weather',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
APPEND_SLASH = False

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

WSGI_APPLICATION = 'config.wsgi.application'

USE_SQLITE = os.getenv('USE_SQLITE', 'False').lower() in ('1', 'true', 'yes')

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'earth_energy'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
    DATABASES['default'].update({
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '60')),
        'CONN_HEALTH_CHECKS': True,
    })

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

REDIS_URL = os.getenv('REDIS_URL', '').strip()
CACHE_KEY_PREFIX = os.getenv('CACHE_KEY_PREFIX', 'earth-energy').strip()

if not DEBUG and not REDIS_URL:
    raise ImproperlyConfigured(
        'REDIS_URL must point to a shared Redis service when DEBUG is False.'
    )

if REDIS_URL and not REDIS_URL.startswith(('redis://', 'rediss://', 'unix://')):
    raise ImproperlyConfigured('REDIS_URL must use redis://, rediss://, or unix://.')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': CACHE_KEY_PREFIX,
            'TIMEOUT': 300,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'health_check_interval': 30,
                    'socket_connect_timeout': 2,
                    'socket_timeout': 2,
                },
            },
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'earth-energy-local',
        }
    }

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'accounts.authentication.AccessTokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'EXCEPTION_HANDLER': 'accounts.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'login': '10/minute',
        'register': '5/hour',
        'refresh': '30/minute',
        'contact': '5/hour',
        'roi_calculate': '2/day',
    },
    'NUM_PROXIES': int(os.getenv('NUM_PROXIES', '0' if DEBUG else '1')),
}

# Dual JWT secrets (access Bearer header + refresh httpOnly cookie)
ACCESS_TOKEN_LIFETIME_MINUTES = int(os.getenv('ACCESS_TOKEN_LIFETIME_MINUTES', '15'))
REFRESH_TOKEN_LIFETIME_DAYS = int(os.getenv('REFRESH_TOKEN_LIFETIME_DAYS', '7'))

REFRESH_COOKIE_NAME = 'jwt'
REFRESH_COOKIE_SECURE = not DEBUG
REFRESH_COOKIE_SAMESITE = 'Strict'
REFRESH_COOKIE_HTTPONLY = True
REFRESH_COOKIE_PATH = '/'
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() in ('1', 'true', 'yes')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv(
    'SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False'
).lower() in ('1', 'true', 'yes')
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'False').lower() in ('1', 'true', 'yes')

# Gemini for ROI (falls back to heuristic if unset / unreachable)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' if os.getenv('SMTP_HOST') else 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = os.getenv('SMTP_HOST', '')
EMAIL_PORT = int(os.getenv('SMTP_PORT', '587') or 587)
EMAIL_HOST_USER = os.getenv('SMTP_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('SMTP_PASS', '')
EMAIL_USE_TLS = EMAIL_PORT != 465
EMAIL_USE_SSL = EMAIL_PORT == 465
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_FROM', 'no-reply@earthenergy.local')
COMPANY_NAME = os.getenv('COMPANY_NAME', 'Earth Solutions')
