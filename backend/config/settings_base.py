"""Shared application settings. Environment policy lives in the named profiles."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTALLED_APPS = [
    'models', 'django.contrib.admin', 'django.contrib.auth',
    'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages',
    'django.contrib.staticfiles', 'rest_framework', 'rest_framework.authtoken', 'corsheaders',
]
MIDDLEWARE = [
    'security.middleware.ProxyBoundaryMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'security.middleware.OperationalMiddleware',
    'security.middleware.IngressGuardMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'middleware.document_upload.DocumentUploadMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = USE_TZ = True
STATIC_URL = '/static/'
MEDIA_URL = None  # There is no public upload/media route.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'security.authentication.ExpiringTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'EXCEPTION_HANDLER': 'security.exceptions.safe_exception_handler',
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
}
TOKEN_TTL_SECONDS = 3600
DATA_UPLOAD_MAX_MEMORY_SIZE = 256 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 20
DATA_UPLOAD_MAX_NUMBER_FILES = 1
DOCUMENT_ANALYSIS_RATE = '6/min'
DOCUMENT_USER_RATE = '6/min'
DOCUMENT_IP_RATE = '12/min'
API_IP_RATE = '60/min'
AUTH_IP_RATE = '5/min'
RATE_LIMIT_MAX_BUCKETS = 10000
DOCUMENT_ANALYSIS_LIMITS = {
    'max_file_bytes': 10 * 1024 * 1024, 'max_pages': 5,
    'max_dimension': 8000, 'max_page_pixels': 16_000_000,
    'max_document_pixels': 50_000_000, 'timeout_seconds': 120,
    'max_worker_rss_bytes': 5 * 1024**3,
}
DOCUMENT_OCR_CONFIGURATION = {
    'detection_size': 'medium', 'recognition_size': 'medium',
    'recognition_batch_size': 1, 'cpu_threads': 4, 'detector_side': 1600,
    'enable_mkldnn': False, 'engine': 'paddle_static',
}
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'no-referrer'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
CORS_ALLOW_CREDENTIALS = False  # SPA sends explicit in-memory tokens, not cookies.
CORS_EXPOSE_HEADERS = ['Retry-After']
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False
DEFAULT_EXCEPTION_REPORTER_FILTER = 'security.observability.PrivateExceptionReporterFilter'
CSRF_FAILURE_VIEW = 'security.exceptions.csrf_failure'
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
LOGGING = {
    'version': 1, 'disable_existing_loggers': True,
    'formatters': {'private': {'()': 'security.observability.OperationalFormatter'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'private'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'operations': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'gunicorn.error': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
