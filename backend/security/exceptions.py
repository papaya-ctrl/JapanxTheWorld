import logging
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.views import exception_handler


def safe_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logging.getLogger('operations').error('internal_error', extra={'event': 'internal_error'})
        response = Response({'code': 'INTERNAL_ERROR', 'message': 'The request could not be completed.'}, status=500)
    elif response.status_code in (401, 403):
        response.data = {'code': 'AUTH_REQUIRED' if response.status_code == 401 else 'ACCESS_DENIED',
                         'message': 'Sign in again to continue.' if response.status_code == 401 else 'You do not have access to this action.'}
    elif response.status_code == 503:
        response.data = {'code': 'SERVICE_BUSY', 'message': 'The server is temporarily unavailable.'}
        response['Retry-After'] = '2'
    response['Cache-Control'] = 'no-store'
    return response


def csrf_failure(request, reason=''):
    return JsonResponse({'code': 'CSRF_FAILED', 'message': 'The session could not be verified. Sign in again.'}, status=403, headers={'Cache-Control': 'no-store'})
