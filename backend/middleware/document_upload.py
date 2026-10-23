"""Upload limits only for the document endpoint; other application flows unchanged."""
from django.core.files.uploadhandler import FileUploadHandler, StopUpload
from django.http import JsonResponse
from services.ocr.limits import DocumentLimits


class BoundedDocumentUpload(FileUploadHandler):
    """Keep a bounded upload in memory, never Django's temporary-file storage."""
    def __init__(self, request, maximum):
        super().__init__(request)
        self.maximum = maximum
        self.received = 0
        self.files = 0
        self.buffer = None

    def new_file(self, *args, **kwargs):
        from io import BytesIO
        super().new_file(*args, **kwargs)
        self.files += 1
        if self.files > 1:
            self.request.document_upload_error = "MULTIPLE_FILES"
            raise StopUpload(connection_reset=True)
        self.buffer = BytesIO()

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > self.maximum:
            self.request.document_upload_error = "FILE_TOO_LARGE"
            self.buffer.close()
            raise StopUpload(connection_reset=True)
        self.buffer.write(raw_data)
        return None

    def file_complete(self, file_size):
        from django.core.files.uploadedfile import InMemoryUploadedFile
        self.buffer.seek(0)
        return InMemoryUploadedFile(self.buffer, self.field_name, self.file_name,
                                    self.content_type, file_size, self.charset)

    def upload_interrupted(self):
        if self.buffer:
            self.buffer.close()


class DocumentUploadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        handler = None
        if request.path.rstrip("/") == "/api/documents/analyze":
            from django.conf import settings
            maximum = DocumentLimits(**getattr(settings, "DOCUMENT_ANALYSIS_LIMITS", {})).max_file_bytes
            try:
                length = int(request.META.get("CONTENT_LENGTH") or 0)
            except (TypeError, ValueError):
                return JsonResponse({"code": "INVALID_REQUEST", "message": "Invalid request length."}, status=400)
            if length > maximum + 64 * 1024:
                return JsonResponse({"code": "FILE_TOO_LARGE", "message": "The upload exceeds the request size limit."}, status=413)
            handler = BoundedDocumentUpload(request, maximum)
            request.upload_handlers = [handler]
        try:
            response = self.get_response(request)
        finally:
            if handler and handler.buffer is not None:
                handler.buffer.close()
        if request.path.rstrip("/") == "/api/documents/analyze":
            response["Cache-Control"] = "no-store"
            response["Pragma"] = "no-cache"
        return response
