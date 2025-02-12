from pathlib import Path
import os
from dotenv import load_dotenv
import sys

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = os.getenv('DJANGO_DEBUG') == 'True'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS').split(',')

IS_RUNSERVER = 'runserver' in sys.argv

INTERNAL_API_URL = 'http://localhost:8000/api' if IS_RUNSERVER else 'http://nginx/api'

IGNORE_SENSORS = [s.strip() for s in os.getenv('IGNORE_SENSORS', '').split(',') if s.strip()]

DOMAIN = os.getenv('DOMAIN')

SECURE_SSL_REDIRECT = False # using AWS Load Balancer + Certs

if os.getenv('BEHIND_SSL_PROXY') == 'True':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

# Cookie Settings
# Estos settings aseguran que las cookies solo se envíen por HTTPS en producción
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE') == 'True'  # Cookie de CSRF solo por HTTPS
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE') == 'True'  # Cookie de sesión solo por HTTPS

# CSRF and CORS Settings
CSRF_TRUSTED_ORIGINS = [
    f'https://{DOMAIN}',  # Acepta CSRF desde HTTPS
    f'http://{DOMAIN}',   # Acepta CSRF desde HTTP (desarrollo)
    'http://localhost:8000',  # Para desarrollo local
    'http://127.0.0.1:8000',  # Para desarrollo local
]
CORS_ALLOWED_ORIGINS = [f'https://{DOMAIN}', f'http://{DOMAIN}']
CORS_ALLOW_CREDENTIALS = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',
    'rest_framework',
    'django_filters',
    'corsheaders',
    'core',
    'plotly',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Add this before CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_LOCAL') if IS_RUNSERVER else os.getenv('DB_HOST'),
        'PORT': '5432',
    }
}


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

LANGUAGE_CODE = os.getenv('DJANGO_DEFAULT_LANGUAGE_CODE')
TIME_ZONE = os.getenv('DJANGO_TIMEZONE') 
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATICFILES_DIRS = [ BASE_DIR / 'core' / 'static' ]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 1000
}
