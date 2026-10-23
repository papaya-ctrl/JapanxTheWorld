"""Never serialize free-form log messages, exception values or request objects."""
import json
import logging
import math
import time
from django.views.debug import SafeExceptionReporterFilter

ROUTES = {'ocr', 'auth', 'checklist', 'health', 'public', 'other'}
EVENTS = {'request', 'ocr', 'rate_rejected', 'internal_error', 'server'}
ERROR_CODES = {'AUTH_REQUIRED','ACCESS_DENIED','CSRF_FAILED','RATE_LIMITED','SERVICE_BUSY',
               'INVALID_REQUEST','INVALID_DOCUMENT','UNSUPPORTED_FILE_TYPE','FILE_TOO_LARGE',
               'REQUEST_TOO_LARGE','DOCUMENT_LIMIT_EXCEEDED','ANALYSIS_MEMORY_LIMIT',
               'ANALYSIS_TIMEOUT','ANALYSIS_BUSY','OCR_UNAVAILABLE','DOCUMENT_UNREADABLE',
               'ANALYSIS_FAILED','INTERNAL_ERROR','INVALID_CREDENTIALS','REGISTRATION_CLOSED'}


class OperationalFormatter(logging.Formatter):
    converter = time.gmtime
    def format(self, record):
        try:
            timestamp = self.formatTime(record, '%Y-%m-%dT%H:%M:%SZ')
        except (ValueError, OverflowError, TypeError):
            timestamp = 'unavailable'
        level = record.levelname
        event = getattr(record, 'event', None)
        output = {'time': timestamp, 'level': level if type(level) is str and level in {'DEBUG','INFO','WARNING','ERROR','CRITICAL'} else 'INFO',
                  'event': event if type(event) is str and event in EVENTS else 'server'}
        route = getattr(record, 'route', None)
        if type(route) is str and route in ROUTES:
            output['route'] = route
        code = getattr(record, 'code', None)
        if type(code) is str and code in ERROR_CODES:
            output['code'] = code
        for name in ('status', 'durationSeconds', 'peakRssMiB'):
            value = getattr(record, name, None)
            maximum = {'status':599, 'durationSeconds':86400, 'peakRssMiB':65536}[name]
            if type(value) in (int, float) and 0 <= value <= maximum and math.isfinite(value):
                output[name] = round(value, 4)
        return json.dumps(output, separators=(',', ':'))


class PrivateExceptionReporterFilter(SafeExceptionReporterFilter):
    def get_post_parameters(self, request):
        return {}

    def get_request_meta(self, request):
        return {}

    def get_traceback_frame_variables(self, request, tb_frame):
        return []

    def get_safe_request_meta(self, request):
        return {}
