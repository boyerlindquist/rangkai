"""
Django settings for Smart Wedding Engine.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-key-change-in-production-!@#$%')

DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if h.strip()]
if 'testserver' not in ALLOWED_HOSTS and (DEBUG or 'test' in os.sys.argv):
    ALLOWED_HOSTS.append('testserver')

# =============================================================================
# Application Definition
# =============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Third-party
    'django_htmx',
    # Local apps
    'core.apps.CoreConfig',
    'finances.apps.FinancesConfig',
    'guests.apps.GuestsConfig',
    'vendors.apps.VendorsConfig',
    'operations.apps.OperationsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.WorkspaceMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.workspace_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# =============================================================================
# Database — PostgreSQL when DATABASE_URL is set, fallback to SQLite
# =============================================================================
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    import urllib.parse
    url = urllib.parse.urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or 5432,
            'CONN_MAX_AGE': int(os.getenv('DJANGO_DB_CONN_MAX_AGE', '600')),
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,
            },
        }
    }

# =============================================================================
# Password validation
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# Internationalization
# =============================================================================
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# =============================================================================
# Static files
# =============================================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# =============================================================================
# Auth & Session Persistence & Security
# =============================================================================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
SESSION_COOKIE_NAME = 'rangkai_sessionid'
CSRF_COOKIE_NAME = 'rangkai_csrftoken'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days

# Reverse proxy SSL & CSRF support for production
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
csrf_env = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://43.173.40.113,https://43.173.40.113,http://localhost:8008,http://127.0.0.1:8008')
CSRF_TRUSTED_ORIGINS = []
for origin in csrf_env.split(','):
    origin = origin.strip()
    if not origin:
        continue
    if not origin.startswith(('http://', 'https://')):
        CSRF_TRUSTED_ORIGINS.append(f'http://{origin}')
        CSRF_TRUSTED_ORIGINS.append(f'https://{origin}')
    else:
        CSRF_TRUSTED_ORIGINS.append(origin)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# Email Configuration (Password Reset & Transactional Emails)
# Uses SMTP when EMAIL_HOST is set in .env; falls back to console backend in local dev.
# =============================================================================
EMAIL_HOST = os.getenv('EMAIL_HOST', '').strip()
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Rangkai.click <noreply@rangkai.click>')
PASSWORD_RESET_TIMEOUT = 60 * 60  # 1 hour

# =============================================================================
# Sumopod Managed Payment Gateway (QRIS)
# Leave SUMOPOD_API_KEY empty in local dev to keep simulated checkout mode.
# =============================================================================
SUMOPOD_API_KEY = os.getenv('SUMOPOD_API_KEY', '').strip()
SUMOPOD_BASE_URL = os.getenv(
    'SUMOPOD_BASE_URL',
    'https://api-pay-sandbox.sumopod.com/api/v1',
).strip().rstrip('/')
SUMOPOD_WEBHOOK_TOKEN = os.getenv('SUMOPOD_WEBHOOK_TOKEN', '').strip()
SUMOPOD_WEBHOOK_SECRET = os.getenv('SUMOPOD_WEBHOOK_SECRET', '').strip()
SUMOPOD_FORWARD_WEBHOOK_URL = os.getenv('SUMOPOD_FORWARD_WEBHOOK_URL', '').strip()
SUMOPOD_EXPIRES_IN_HOURS = int(os.getenv('SUMOPOD_EXPIRES_IN_HOURS', '24'))
SUMOPOD_TEST_AMOUNT = int(os.getenv('SUMOPOD_TEST_AMOUNT', '0') or '0')
