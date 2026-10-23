"""The sole document-upload analysis path: validation, local worker, schema."""
from middleware.file_validator import read_validated_upload
from models.schemas import DocumentUploadResultSchema
from services.ocr.worker import get_document_worker


def analyze_uploaded_document(uploaded_file):
    worker = get_document_worker()
    data, kind = read_validated_upload(uploaded_file, worker.limits)
    result = worker.analyze(data, kind)
    # Aliases preserve useful legacy fields without inventing urgency or advice.
    return DocumentUploadResultSchema.model_validate({
        **result, "source": "deterministic", "deadline": result["primaryDeadline"],
        "urgency": None, "relatedGuide": None,
        "officialWarning": " ".join(result["warnings"]) or None,
    }).model_dump(mode="json")
