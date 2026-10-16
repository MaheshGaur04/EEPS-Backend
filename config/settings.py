"""Django settings for Earth Energy."""

from pathlib import Path
import os
from urllib.parse import urlparse

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-only-change-me')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
CORS_ALLOWED_ORIGINS = [
    origin.strip().rstrip('/')
    for origin in os.getenv('CORS_ALLOWED_ORIGINS', FRONTEND_URL).split(',')
    if origin.strip()
]

ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET', SECRET_KEY)
REFRESH_TOKEN_SECRET = os.getenv('REFRESH_TOKEN_SECRET', SECRET_KEY)
USE_SQLITE = os.getenv('USE_SQLITE', 'False').lower() in ('1', 'true', 'yes')

if not DEBUG:
    production_secrets = {
        'SECRET_KEY': SECRET_KEY,
        'ACCESS_TOKEN_SECRET': ACCESS_TOKEN_SECRET,
        'REFRESH_TOKEN_SECRET': REFRESH_TOKEN_SECRET,
    }
    for name, value in production_secrets.items():
        if value.startswith('django-insecure-') or len(value) < 50 or len(set(value)) < 5:
            raise ImproperlyConfigured(f'{name} must be a strong, unique production secret.')
    if len(set(production_secrets.values())) != len(production_secrets):
        raise ImproperlyConfigured('SECRET_KEY, ACCESS_TOKEN_SECRET, and REFRESH_TOKEN_SECRET must differ.')
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured('ALLOWED_HOSTS must be set for production.')
    frontend_origin = urlparse(FRONTEND_URL)
    if (
        frontend_origin.scheme != 'https'
        or not frontend_origin.netloc
        or frontend_origin.path not in ('', '/')
        or frontend_origin.query
        or frontend_origin.fragment
    ):
        raise ImproperlyConfigured('FRONTEND_URL must be an HTTPS origin in production.')
    if USE_SQLITE:
        raise ImproperlyConfigured('SQLite is not supported for production deployments.')
    if not os.getenv('DATABASE_URL') and not all(
        os.getenv(name) for name in ('DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST')
    ):
        raise ImproperlyConfigured('Set DATABASE_URL or all required DB_* variables for production.')

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
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif os.getenv('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.parse(
            os.environ['DATABASE_URL'],
            conn_max_age=600,
            conn_health_checks=True,
        )
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

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'accounts.authentication.AccessTokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'EXCEPTION_HANDLER': 'accounts.exceptions.custom_exception_handler',
}

# Dual JWT secrets (access Bearer header + refresh httpOnly cookie)
ACCESS_TOKEN_LIFETIME_MINUTES = int(os.getenv('ACCESS_TOKEN_LIFETIME_MINUTES', '15'))
REFRESH_TOKEN_LIFETIME_DAYS = int(os.getenv('REFRESH_TOKEN_LIFETIME_DAYS', '7'))

REFRESH_COOKIE_NAME = 'jwt'
REFRESH_COOKIE_SECURE = not DEBUG
REFRESH_COOKIE_SAMESITE = os.getenv('REFRESH_COOKIE_SAMESITE', 'Strict')
REFRESH_COOKIE_HTTPONLY = True
REFRESH_COOKIE_PATH = '/'
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000' if not DEBUG else '0'))

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
