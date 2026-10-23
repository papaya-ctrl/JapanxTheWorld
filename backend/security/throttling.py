from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle
from .rate_limit import consume, RateStoreUnavailable


class LimitsUnavailable(APIException):
    status_code = 503
    default_detail = 'The server is temporarily unavailable.'
    default_code = 'service_busy'


class DocumentUserThrottle(BaseThrottle):
    def allow_request(self, request, view):
        if not getattr(settings, 'ATOMIC_RATE_LIMITING', False): return True
        if not request.user or not request.user.is_authenticated: return False
        try:
            self.delay = consume('ocr_user', str(request.user.pk), settings.DOCUMENT_USER_RATE)
        except RateStoreUnavailable:
            raise LimitsUnavailable() from None
        return self.delay == 0

    def wait(self): return getattr(self, 'delay', 60)
