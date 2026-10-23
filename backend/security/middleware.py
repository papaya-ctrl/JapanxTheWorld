import ipaddress
import logging
import re
import time
from django.conf import settings
from django.http import JsonResponse
from django.utils.http import parse_header_parameters
from .rate_limit import consume, RateStoreUnavailable


def route_category(path):
    if path.rstrip('/') == '/api/documents/analyze': return 'ocr'
    if path.startswith('/api/auth/'): return 'auth'
    if path.startswith('/api/checklist'): return 'checklist'
    if path.rstrip('/') in {'/api/health', '/api/ready'}: return 'health'
    if path.startswith(('/api/guides', '/api/resources')): return 'public'
    return 'other'


def reject(code, message, status, retry=None):
    response = JsonResponse({'code': code, 'message': message}, status=status, headers={'Cache-Control': 'no-store', 'Pragma': 'no-cache'})
    response.operational_error = code
    if retry: response['Retry-After'] = str(retry)
    return response


class ProxyBoundaryMiddleware:
    def __init__(self, get_response): self.get_response = get_response

    def __call__(self, request):
        trusted = request.META.get('REMOTE_ADDR') in getattr(settings, 'TRUSTED_PROXY_IPS', [])
        for name in ('HTTP_FORWARDED', 'HTTP_X_FORWARDED_HOST', 'HTTP_X_FORWARDED_FOR'):
            request.META.pop(name, None)
        if not trusted:
            request.META.pop('HTTP_X_FORWARDED_PROTO', None)
            request.META.pop('HTTP_X_REAL_IP', None)
        elif request.META.get('HTTP_X_FORWARDED_PROTO') not in (None, 'http', 'https'):
            return reject('INVALID_REQUEST', 'Invalid proxy request.', 400)
        candidate = request.META.get('HTTP_X_REAL_IP') if trusted else None
        candidate = candidate or request.META.get('REMOTE_ADDR', '')
        try:
            request.client_ip = str(ipaddress.ip_address(candidate))
        except ValueError:
            if getattr(settings, 'PRODUCTION', False):
                return reject('INVALID_REQUEST', 'Invalid network request.', 400)
            request.client_ip = 'unknown'
        return self.get_response(request)


class IngressGuardMiddleware:
    def __init__(self, get_response): self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'ATOMIC_RATE_LIMITING', False) or not request.path.startswith('/api/'):
            return self.get_response(request)
        category = route_category(request.path)
        _, parameters = parse_header_parameters(request.META.get('CONTENT_TYPE', ''))
        if parameters.get('charset', 'utf-8').lower() not in {'utf-8', 'utf8', 'us-ascii', 'ascii'}:
            return reject('INVALID_REQUEST', 'Use UTF-8 request metadata.', 415)
        request.encoding = 'utf-8'
        if request.method in {'POST', 'PUT', 'PATCH'}:
            length = request.META.get('CONTENT_LENGTH', '')
            if not length:
                return reject('LENGTH_REQUIRED', 'A bounded Content-Length is required.', 411)
            if len(length) > 20 or not re.fullmatch(r'[0-9]+', length):
                return reject('INVALID_REQUEST', 'Invalid request length.', 400)
            maximum = settings.DOCUMENT_ANALYSIS_LIMITS['max_file_bytes'] + 64*1024 if category == 'ocr' else 64*1024
            if int(length) > maximum:
                return reject('REQUEST_TOO_LARGE', 'The request exceeds the size limit.', 413)
        scopes = [('api_ip', settings.API_IP_RATE)]
        if category == 'ocr': scopes.append(('ocr_ip', settings.DOCUMENT_IP_RATE))
        if category == 'auth' and request.method == 'POST': scopes.append(('auth_ip', settings.AUTH_IP_RATE))
        try:
            for scope, rate in scopes:
                wait = consume(scope, request.client_ip, rate)
                if wait:
                    return reject('RATE_LIMITED', 'Too many requests. Please wait before trying again.', 429, wait)
        except RateStoreUnavailable:
            return reject('SERVICE_BUSY', 'The server is temporarily unavailable.', 503, 2)
        return self.get_response(request)


class OperationalMiddleware:
    def __init__(self, get_response): self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        category = route_category(request.path)
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-store'
            response['Pragma'] = 'no-cache'
            response['X-Content-Type-Options'] = 'nosniff'
            response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
            response['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            logging.getLogger('operations').info('request', extra={'event': 'request', 'route': category,
                'status': response.status_code, 'durationSeconds': time.monotonic()-start,
                'code': getattr(response, 'operational_error', None) or (getattr(response, 'data', {}).get('code') if isinstance(getattr(response, 'data', None), dict) else None)})
        return response
