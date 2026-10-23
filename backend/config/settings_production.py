"""Fail-closed public-server settings; never loads a .env file implicitly."""
import ipaddress
import logging
import os
import re
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured
from .settings_base import *  # noqa: F403


def required(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise ImproperlyConfigured(f'{name} must be configured for production.')
    return value


def boolean(name, default=False):
    value = os.environ.get(name, str(default)).lower()
    if value not in {'true', 'false'}:
        raise ImproperlyConfigured(f'{name} must be true or false.')
    return value == 'true'


def exact_host(value):
    if value in {'localhost', 'testserver'} or '*' in value or value.startswith('.'):
        raise ImproperlyConfigured('Use exact public hosts; wildcards and development hosts are forbidden.')
    try:
        address = ipaddress.ip_address(value.strip('[]'))
        if address.is_loopback or address.is_unspecified:
            raise ImproperlyConfigured('Production hosts cannot be loopback or unspecified addresses.')
    except ValueError:
        if len(value)>253 or '.' not in value or not all(re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?', label) for label in value.split('.')):
            raise ImproperlyConfigured('Use exact DNS hosts without schemes, ports or paths.')
    return value


def origins(name):
    result = []
    for value in required(name).split(','):
        value = value.strip()
        try:
            parsed = urlsplit(value)
            valid = parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and not parsed.path
            if not valid or (parsed.port is not None and not 1 <= parsed.port <= 65535):
                raise ValueError()
            exact_host(parsed.hostname)
        except ValueError:
            raise ImproperlyConfigured(f'{name} requires exact HTTPS origins without paths or credentials.') from None
        result.append(value)
    return result


def absolute_path(name):
    value = Path(required(name)).expanduser()
    if not value.is_absolute():
        raise ImproperlyConfigured(f'{name} must be an absolute path.')
    return value.resolve()


PRODUCTION = True
logging.raiseExceptions = False  # Logging failures must never dump original records.
DEBUG = False
if boolean('DJANGO_DEBUG'):
    raise ImproperlyConfigured('Production cannot enable DEBUG.')
SECRET_KEY = required('DJANGO_SECRET_KEY')
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 8 or SECRET_KEY.startswith('django-insecure-') or 'development' in SECRET_KEY.lower() or 'replace' in SECRET_KEY.lower():
    raise ImproperlyConfigured('Generate a new strong production DJANGO_SECRET_KEY.')
SECRET_KEY_FALLBACKS = []  # Never accept a committed development key during rotation.
ALLOWED_HOSTS = [exact_host(v.strip()) for v in required('DJANGO_ALLOWED_HOSTS').split(',')]
CORS_ALLOWED_ORIGINS = origins('DJANGO_CORS_ALLOWED_ORIGINS')
CSRF_TRUSTED_ORIGINS = origins('DJANGO_CSRF_TRUSTED_ORIGINS')
TRUSTED_PROXY_IPS = [v.strip() for v in required('DJANGO_TRUSTED_PROXY_IPS').split(',')]
try:
    for value in TRUSTED_PROXY_IPS:
        ipaddress.ip_address(value)
except ValueError:
    raise ImproperlyConfigured('DJANGO_TRUSTED_PROXY_IPS must contain exact IP addresses.') from None
STATE_DIR = absolute_path('DJANGO_STATE_DIR')
STATIC_ROOT = absolute_path('DJANGO_STATIC_ROOT')
DOCUMENT_OCR_MODEL_ROOT = absolute_path('DOCUMENT_OCR_MODEL_ROOT')
if STATE_DIR.is_relative_to(BASE_DIR.parent) or STATE_DIR == Path('/'):
    raise ImproperlyConfigured('Keep private production state outside the source checkout.')
if BASE_DIR.parent.is_relative_to(STATIC_ROOT):
    raise ImproperlyConfigured('The public static root cannot contain the source checkout.')
if any(a.is_relative_to(b) or b.is_relative_to(a) for a,b in [(STATIC_ROOT,STATE_DIR),(STATIC_ROOT,DOCUMENT_OCR_MODEL_ROOT)]):
    raise ImproperlyConfigured('Public static files must be separate from private state and model storage.')
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': STATE_DIR / 'app.sqlite3', 'OPTIONS': {'timeout': 10}}}
RATE_LIMIT_DB = STATE_DIR / 'rate-limits.sqlite3'
ATOMIC_RATE_LIMITING = True
DOCUMENT_OCR_LOCK_PATH = STATE_DIR / 'ocr-worker.lock'
FILE_UPLOAD_TEMP_DIR = str(STATE_DIR / 'tmp')  # OCR uploads never use the disk handler.
DOCUMENT_REQUIRE_AUTH = True
ALLOW_ANONYMOUS_CHECKLIST = False
ALLOW_REGISTRATION = False
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated']}
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = False
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = boolean('DJANGO_HSTS_INCLUDE_SUBDOMAINS')
SECURE_HSTS_PRELOAD = boolean('DJANGO_HSTS_PRELOAD')
if SECURE_HSTS_PRELOAD and not SECURE_HSTS_INCLUDE_SUBDOMAINS:
    raise ImproperlyConfigured('HSTS preload requires verified HTTPS for every subdomain.')
