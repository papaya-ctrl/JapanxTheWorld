from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent
from rest_framework.decorators import api_view, authentication_classes, parser_classes, permission_classes, throttle_classes
from rest_framework.exceptions import ParseError, UnsupportedMediaType
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from services.documentAnalysis.upload import analyze_uploaded_document
from services.ocr.errors import DocumentProcessingError
from security.permissions import DocumentAccess
from security.throttling import DocumentUserThrottle
from rest_framework.permissions import AllowAny


def error_response(code, message, http_status):
    headers = {"Cache-Control": "no-store", "Pragma": "no-cache"}
    if http_status == 503:
        headers["Retry-After"] = "2"
    return Response({"code": code, "message": message}, status=http_status, headers=headers)


class DocumentAnalysisThrottle(SimpleRateThrottle):
    scope = "document_analysis"

    def get_rate(self):
        from django.conf import settings
        return getattr(settings, "DOCUMENT_ANALYSIS_RATE", "6/min")

    def get_cache_key(self, request, view):
        from django.conf import settings
        if getattr(settings, 'ATOMIC_RATE_LIMITING', False):
            return None
        return self.cache_format % {"scope": self.scope, "ident": getattr(request._request, 'client_ip', 'unknown')}


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})


@api_view(['GET'])
@permission_classes([DocumentAccess])
def document_access_check(request):
    """Proxy authorization subrequest: no upload parsing, worker or user payload."""
    return Response(status=204, headers={'Cache-Control': 'no-store'})


@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@permission_classes([DocumentAccess])
@throttle_classes([DocumentAnalysisThrottle, DocumentUserThrottle])
def analyze_document(request):
    try:
        # Parsing first triggers the endpoint-specific bounded upload handler.
        files = request.FILES
        upload_error = getattr(request._request, "document_upload_error", None)
        if upload_error:
            return error_response(upload_error, "Upload one supported document within the file size limit.",
                                  413 if upload_error == "FILE_TOO_LARGE" else 400)
        if len(files.getlist("file")) != 1 or sum(len(files.getlist(k)) for k in files) != 1:
            return error_response("INVALID_REQUEST", "Upload one document in the 'file' field.", 400)
        # Extra text and document hints are never used as document evidence.
        result = analyze_uploaded_document(files["file"])
        # Uploads and results are deliberately not sent to legacy persistence.
        return Response(result, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
    except DocumentProcessingError as exc:
        return error_response(exc.code, exc.message, exc.status)
    except (RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent):
        return error_response("REQUEST_TOO_LARGE", "The upload exceeds the request limits.", 413)
    except UnsupportedMediaType:
        return error_response("UNSUPPORTED_REQUEST_TYPE", "Use a multipart document upload.", 415)
    except ParseError:
        return error_response("INVALID_REQUEST", "The upload request could not be read.", 400)
    except Exception:
        # Never return/log native OCR exceptions, validation inputs, or traces.
        return error_response("ANALYSIS_FAILED", "Document analysis failed. Please try again later.", 500)
