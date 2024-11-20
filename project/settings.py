from pathlib import Path
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = os.getenv('DJANGO_DEBUG') == 'True'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS').split(',')
logger.debug(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
logger.debug(f"DEBUG: {DEBUG}")


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',  # Añadir esta línea
    'core',
    'plotly',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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

STATIC_URL = 'static/'
STATIC_ROOT = os.getenv('DJANGO_STATIC_ROOT')
STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]
MEDIA_URL = 'media/'
MEDIA_ROOT = os.getenv('DJANGO_MEDIA_ROOT')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de LOGGING
LOGGING = {
    'version': 1,  # Versión del esquema de configuración de logging
    'disable_existing_loggers': False,  # No deshabilitar los loggers existentes
    'filters': {
        'require_debug_false': {  # Filtro para requerir que DEBUG sea False
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {  # Filtro para requerir que DEBUG sea True
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {  # Handler que envía los logs a la consola
            'level': 'DEBUG',  # Nivel de log mínimo para este handler
            'class': 'logging.StreamHandler',  # Clase de handler que envía logs a streams (como la consola)
            'filters': ['require_debug_false'],  # Aplicar el filtro require_debug_false a este handler
        },
    },
    'loggers': {
        'django': {  # Logger para mensajes de Django
            'handlers': ['console'],  # Usar el handler de consola para este logger
            'level': 'INFO',  # Nivel de log mínimo para este logger
            'propagate': True,  # Permitir que los logs se propaguen a otros loggers
        },
        'django.server': {  # Logger para mensajes del servidor de Django
            'handlers': ['console'],  # Usar el handler de consola para este logger
            'level': 'DEBUG',  # Cambiado de INFO a DEBUG
            'propagate': False,  # No permitir que los logs se propaguen a otros loggers
        },
    },
}

# Agregar al final del archivo
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}
