"""Explicit local/demo profile. Never use this module for a public server."""
import os
from copy import deepcopy
from dotenv import load_dotenv
from .settings_base import *  # noqa: F403

load_dotenv(BASE_DIR / '.env')
DEBUG = True
PRODUCTION = False
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or 'django-insecure-local-development-only-never-use-on-a-public-server'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.getenv('DJANGO_DB_PATH') or BASE_DIR / 'db.sqlite3'}}
CORS_ALLOWED_ORIGINS = [os.getenv('FRONTEND_URL', 'http://localhost:5173')]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
TRUSTED_PROXY_IPS = []
DOCUMENT_REQUIRE_AUTH = False
ALLOW_ANONYMOUS_CHECKLIST = True
ALLOW_REGISTRATION = True
ATOMIC_RATE_LIMITING = False
DOCUMENT_ANALYSIS_RATE = os.getenv('DOCUMENT_ANALYSIS_RATE', '6/min')
DOCUMENT_OCR_MODEL_ROOT = os.getenv('DOCUMENT_OCR_MODEL_ROOT') or None
DOCUMENT_OCR_LOCK_PATH = os.getenv('DOCUMENT_OCR_LOCK_PATH') or None
STATIC_ROOT = BASE_DIR / 'staticfiles'
LOGGING = deepcopy(LOGGING)
LOGGING['loggers']['operations']['level'] = 'WARNING'
