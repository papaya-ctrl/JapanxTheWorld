import os
from models.db_models import Document, AnalysisResult


def save_analysis_record(
    analysis_data: dict,
    user=None,
    original_filename: str | None = None,
    mime_type: str | None = None,
    raw_extracted_text: str | None = None,
) -> AnalysisResult:
    """
    Saves Document metadata and AnalysisResult to the database.
    PRIVACY RULE: Does NOT store personal document text unless STORE_EXTRACTED_TEXT=true.
    """
    store_raw_text = os.getenv("STORE_EXTRACTED_TEXT", "false").lower() == "true"

    authenticated_user = user if (user and getattr(user, "is_authenticated", False)) else None

    doc = Document.objects.create(
        user=authenticated_user,
        original_filename=original_filename,
        mime_type=mime_type,
        extracted_text=raw_extracted_text if store_raw_text else None,
    )

    result_record = AnalysisResult.objects.create(
        document=doc,
        source=analysis_data["source"],
        document_type=analysis_data["documentType"],
        summary=analysis_data["summary"],
        deadline=analysis_data.get("deadline"),
        urgency=analysis_data["urgency"],
        related_guide=analysis_data.get("relatedGuide"),
    )

    return result_record
