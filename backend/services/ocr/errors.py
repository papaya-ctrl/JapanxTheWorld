"""Public, English errors. Native parser/OCR exceptions never cross the API."""


class DocumentProcessingError(Exception):
    code = "DOCUMENT_UNREADABLE"
    message = "The document could not be read safely. Try a clearer supported document."
    status = 422


class InvalidDocument(DocumentProcessingError):
    code = "INVALID_DOCUMENT"
    message = "The uploaded file is not a valid supported document."
    status = 400


class DocumentLimitExceeded(DocumentProcessingError):
    code = "DOCUMENT_LIMIT_EXCEEDED"
    message = "The document exceeds the supported page, image, or text limits."
    status = 413


class ProcessingTimeout(DocumentProcessingError):
    code = "ANALYSIS_TIMEOUT"
    message = "Document processing exceeded the time limit. Try fewer pages or a smaller image."
    status = 504


class ProcessingMemoryExceeded(DocumentProcessingError):
    code = "ANALYSIS_MEMORY_LIMIT"
    message = "Document processing exceeded the memory limit. Try a smaller document."
    status = 413


class WorkerBusy(DocumentProcessingError):
    code = "ANALYSIS_BUSY"
    message = "Document analysis is busy. Please try again shortly."
    status = 503


class ModelsUnavailable(DocumentProcessingError):
    code = "OCR_UNAVAILABLE"
    message = "Local OCR is unavailable. Please try again later."
    status = 503


ERROR_TYPES = {cls.code: cls for cls in (DocumentProcessingError, InvalidDocument,
    DocumentLimitExceeded, ProcessingTimeout, ProcessingMemoryExceeded, WorkerBusy, ModelsUnavailable)}
