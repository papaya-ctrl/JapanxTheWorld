import os

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

def validate_uploaded_file(uploaded_file) -> tuple[bool, str | None, str | None]:
    if uploaded_file is None:
        return False, "INVALID_REQUEST", "No file provided."

    if uploaded_file.size == 0:
        return False, "EMPTY_FILE", "The uploaded file is empty (0 bytes)."

    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        return False, "FILE_TOO_LARGE", "The uploaded file exceeds the 10MB size limit."

    filename = uploaded_file.name or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return (
            False,
            "UNSUPPORTED_FILE_TYPE",
            f"Unsupported file extension '{ext}'. Allowed formats: JPEG, PNG, WebP, PDF.",
        )

    content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        if content_type != "application/octet-stream":
            return (
                False,
                "UNSUPPORTED_FILE_TYPE",
                f"Unsupported file type '{content_type}'. Allowed formats: JPEG, PNG, WebP, PDF.",
            )

    return True, None, None
