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

# Upload extraction has a separate contract: unknown/unsupported legacy fields
# remain null. The legacy schema above is retained for unrelated callers.
from datetime import date
import math
import re
from pydantic import ConfigDict, Field, StrictInt, model_validator


class ExtractionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ExtractedField(ExtractionModel):
    label: str
    kind: str
    status: Literal["verified", "unverified"]
    reasons: List[str]
    evidenceIds: List[str]
    ocrConfidence: float | None = Field(default=None, ge=0, le=1)
    association: Literal["text_and_geometry", "none"]
    occurrences: int = Field(ge=1)

    @model_validator(mode="after")
    def verified_requires_evidence(self):
        if self.status == "verified" and (not self.evidenceIds or self.reasons or self.association == "none"):
            raise ValueError("Verified fields require associated evidence without uncertainty reasons.")
        return self


class ExtractedDeadline(ExtractedField):
    date: str | None

    @field_validator("date")
    @classmethod
    def valid_iso_date(cls, value):
        if value is not None and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) or date.fromisoformat(value).isoformat() != value):
            raise ValueError("Dates must be ISO calendar dates.")
        return value

    @model_validator(mode="after")
    def verified_date(self):
        if self.status == "verified" and self.date is None:
            raise ValueError("Verified deadlines require a date.")
        return self


class ExtractedAmount(ExtractedField):
    value: StrictInt | None = Field(ge=0)
    currency: Literal["JPY"]

    @model_validator(mode="after")
    def verified_amount(self):
        if self.status == "verified" and self.value is None:
            raise ValueError("Verified amounts require a value.")
        return self


class SourceEvidence(ExtractionModel):
    id: str
    text: str
    confidence: float | None = Field(ge=0, le=1)
    bbox: List[float] = Field(min_length=4, max_length=4)
    polygon: List[List[float]] | None
    page: int = Field(ge=1)
    originalIndex: int = Field(ge=0)
    readingOrder: int = Field(ge=0)
    extractionMethod: Literal["paddleocr", "pdf_embedded_text"]

    @field_validator("bbox")
    @classmethod
    def valid_box(cls, value):
        if not all(math.isfinite(v) for v in value) or value[0] >= value[2] or value[1] >= value[3]:
            raise ValueError("Source rectangles must be finite and positive.")
        return value

    @field_validator("polygon")
    @classmethod
    def valid_polygon(cls, value):
        if value is not None and (len(value) < 4 or any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in value)):
            raise ValueError("Source polygons must contain finite coordinate pairs.")
        return value


class ExtractionPage(ExtractionModel):
    page: int = Field(ge=1)
    method: Literal["paddleocr", "pdf_embedded_text"]
    coordinateSystem: Literal["image_pixels", "rendered_pixels", "pdf_points"]
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    auxiliaryFramesSkipped: int = Field(default=0, ge=0)


class DocumentUploadResultSchema(ExtractionModel):
    source: Literal["deterministic"]
    extractionMethod: Literal["paddleocr", "pdf_embedded_text", "mixed"]
    documentType: str | None
    summary: str | None
    deadline: str | None
    urgency: Literal["low", "important", "urgent"] | None = None
    relatedGuide: str | None = None
    officialWarning: str | None = None
    primaryDeadline: str | None
    deadlines: List[ExtractedDeadline]
    primaryAmount: StrictInt | None = Field(ge=0)
    amounts: List[ExtractedAmount]
    importantPoints: List[str]
    nextSteps: List[str]
    evidence: List[SourceEvidence]
    warnings: List[str]
    extractionStatus: Literal["verified", "partial", "unverified", "no_fields"]
    documentTypeEvidenceIds: List[str]
    completedPaymentEvidenceIds: List[str]
    pages: List[ExtractionPage]

    @model_validator(mode="after")
    def check_contract(self):
        ids = {e.id for e in self.evidence}
        if len(ids) != len(self.evidence):
            raise ValueError("Evidence identifiers must be unique.")
        references = self.documentTypeEvidenceIds + self.completedPaymentEvidenceIds
        for field in self.deadlines + self.amounts:
            references += field.evidenceIds
        if not set(references) <= ids:
            raise ValueError("All field references must identify source evidence.")
        pages = {p.page for p in self.pages}
        if len(pages) != len(self.pages) or any(e.page not in pages for e in self.evidence):
            raise ValueError("Evidence must belong to a declared page.")
        if self.deadline != self.primaryDeadline:
            raise ValueError("The legacy deadline must match the primary deadline.")
        if self.primaryDeadline is not None and not any(d.status == "verified" and d.date == self.primaryDeadline for d in self.deadlines):
            raise ValueError("The primary deadline must have verified evidence.")
        if self.primaryAmount is not None and not any(a.status == "verified" and a.value == self.primaryAmount for a in self.amounts):
            raise ValueError("The primary amount must have verified evidence.")
        prose = [self.documentType, self.summary, self.officialWarning, *self.importantPoints,
                 *self.nextSteps, *self.warnings]
        for field in self.deadlines + self.amounts:
            prose += [field.label, *field.reasons]
        if any(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text) for text in prose if text):
            raise ValueError("Generated descriptions must be in English.")
        return self
