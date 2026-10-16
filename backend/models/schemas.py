from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator

ALLOWED_GUIDES = {
    "address-registration-moving",
    "national-health-insurance",
    "national-pension",
    "residence-tax",
    "residence-status-renewal",
    "student-to-worker",
    "part-time-work-permission",
    "employment-contract",
}

class DocumentAnalysisResultSchema(BaseModel):
    source: Literal["template", "ai"]
    documentType: str
    summary: str
    deadline: Optional[str] = None
    urgency: Literal["low", "important", "urgent"]
    importantPoints: List[str]
    nextSteps: List[str]
    relatedGuide: Optional[str] = None
    officialWarning: str

    @field_validator("documentType", "summary", "officialWarning")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("String field must not be empty.")
        return v.strip()

    @field_validator("deadline")
    @classmethod
    def clean_deadline(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned or cleaned.lower() in {"null", "none", "n/a", "unknown", "not specified", "なし", "不明"}:
            return None
        return cleaned

    @field_validator("relatedGuide")
    @classmethod
    def validate_related_guide(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned in ALLOWED_GUIDES else None