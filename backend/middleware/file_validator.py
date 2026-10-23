"""Bounded reads, extension allowlist and authoritative content-signature checks."""
from pathlib import Path
from services.ocr.errors import InvalidDocument, DocumentLimitExceeded
from services.ocr.limits import DocumentLimits

MAX_FILE_SIZE_BYTES = DocumentLimits().max_file_bytes
MIME_TYPES = {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "pdf": "application/pdf"}
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}


def detect_document_kind(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"%PDF-"):
        return "pdf"
    raise InvalidDocument()


def read_validated_upload(uploaded_file, limits: DocumentLimits) -> tuple[bytes, str]:
    if uploaded_file is None:
        raise InvalidDocument()
    if Path(getattr(uploaded_file, 'name', '') or '').suffix.lower() not in EXTENSIONS:
        error = InvalidDocument()
        error.code = 'UNSUPPORTED_FILE_TYPE'
        error.message = 'Use a JPEG, PNG, WebP, or PDF filename and supported file contents.'
        raise error
    uploaded_file.seek(0)
    try:
        data = uploaded_file.read(limits.max_file_bytes + 1)
    finally:
        uploaded_file.seek(0)
    if not data:
        error = InvalidDocument()
        error.code, error.message = "EMPTY_FILE", "The uploaded file is empty."
        raise error
    if len(data) > limits.max_file_bytes:
        raise DocumentLimitExceeded()
    try:
        kind = detect_document_kind(data)
    except InvalidDocument:
        error = InvalidDocument()
        error.code = "UNSUPPORTED_FILE_TYPE"
        error.message = "Supported document formats are JPEG, PNG, WebP, and PDF."
        raise error from None
    declared = (getattr(uploaded_file, "content_type", "") or "").lower()
    if declared not in ("", "application/octet-stream", MIME_TYPES[kind]):
        raise InvalidDocument()
    return data, kind


def validate_uploaded_file(uploaded_file) -> tuple[bool, str | None, str | None]:
    """Compatibility helper; complete decoding happens inside the limited worker."""
    try:
        read_validated_upload(uploaded_file, DocumentLimits())
    except (InvalidDocument, DocumentLimitExceeded) as exc:
        return False, exc.code, exc.message
    return True, None, None
