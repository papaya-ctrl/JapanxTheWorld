import type { DocumentAnalysisResult, DocumentUploadResult, ExtractedField, LegacyDocumentAnalysisResult } from "../types";
import { isISODate } from "../lib/documentDates";

const record = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === "string");
const nullableString = (v: unknown) => v === null || typeof v === "string";
const number = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const integer = (v: unknown, minimum = 0): v is number => number(v) && Number.isSafeInteger(v) && v >= minimum;
const confidence = (v: unknown) => v === null || (number(v) && v >= 0 && v <= 1);
const date = (v: unknown) => v === null || isISODate(v);
const method = (v: unknown) => v === "paddleocr" || v === "pdf_embedded_text";
const urgency = (v: unknown) => v === "low" || v === "important" || v === "urgent";
const box = (v: unknown) => Array.isArray(v) && v.length === 4 && v.every(number) && v[0] < v[2] && v[1] < v[3];
const field = (v: unknown): v is ExtractedField & Record<string, unknown> => record(v)
  && typeof v.label === "string" && typeof v.kind === "string"
  && (v.status === "verified" || v.status === "unverified") && strings(v.reasons) && strings(v.evidenceIds)
  && confidence(v.ocrConfidence) && (v.association === "none" || v.association === "text_and_geometry")
  && integer(v.occurrences, 1)
  && (v.status !== "verified" || (v.evidenceIds.length > 0 && !v.reasons.length && v.association !== "none"));

export function isLegacyDocumentAnalysisResult(v: unknown): v is LegacyDocumentAnalysisResult {
  return record(v) && (v.source === "template" || v.source === "ai")
    && typeof v.documentType === "string" && typeof v.summary === "string"
    && date(v.deadline) && urgency(v.urgency) && strings(v.importantPoints) && strings(v.nextSteps)
    && nullableString(v.relatedGuide) && typeof v.officialWarning === "string";
}

/** No coercion/defaults: missing required fields are malformed, never invented. */
export function isDocumentUploadResult(v: unknown): v is DocumentUploadResult {
  if (!record(v) || v.source !== "deterministic"
    || !(method(v.extractionMethod) || v.extractionMethod === "mixed")
    || !nullableString(v.documentType) || !nullableString(v.summary) || !nullableString(v.officialWarning)
    || !(v.urgency === null || urgency(v.urgency)) || !nullableString(v.relatedGuide)
    || !date(v.deadline) || !date(v.primaryDeadline) || v.deadline !== v.primaryDeadline
    || !(v.primaryAmount === null || integer(v.primaryAmount))
    || !strings(v.importantPoints) || !strings(v.nextSteps) || !strings(v.warnings)
    || !["verified", "partial", "unverified", "no_fields"].includes(String(v.extractionStatus))
    || !strings(v.documentTypeEvidenceIds) || !strings(v.completedPaymentEvidenceIds)
    || !Array.isArray(v.deadlines) || !Array.isArray(v.amounts) || !Array.isArray(v.evidence) || !Array.isArray(v.pages)) return false;
  if (!v.deadlines.every(x => field(x) && record(x) && date(x.date) && (x.status !== "verified" || x.date !== null))
    || !v.amounts.every(x => field(x) && record(x) && x.currency === "JPY" && (x.value === null || integer(x.value)) && (x.status !== "verified" || x.value !== null))) return false;
  if (!v.pages.every(x => record(x) && integer(x.page, 1) && method(x.method)
    && ["image_pixels", "rendered_pixels", "pdf_points"].includes(String(x.coordinateSystem))
    && number(x.width) && x.width > 0 && number(x.height) && x.height > 0 && integer(x.auxiliaryFramesSkipped))) return false;
  const pageIds = new Set(v.pages.map(x => x.page));
  if (pageIds.size !== v.pages.length || !v.evidence.every(x => record(x) && typeof x.id === "string" && typeof x.text === "string"
    && confidence(x.confidence) && box(x.bbox) && integer(x.page, 1) && pageIds.has(x.page)
    && integer(x.originalIndex) && integer(x.readingOrder) && method(x.extractionMethod)
    && (x.polygon === null || (Array.isArray(x.polygon) && x.polygon.length >= 4 && x.polygon.every(p => Array.isArray(p) && p.length === 2 && p.every(number)))))) return false;
  const ids = new Set(v.evidence.map(x => x.id));
  if (ids.size !== v.evidence.length || ![...v.documentTypeEvidenceIds, ...v.completedPaymentEvidenceIds,
    ...v.deadlines.flatMap(x => x.evidenceIds), ...v.amounts.flatMap(x => x.evidenceIds)].every(id => ids.has(id))) return false;
  if (v.primaryDeadline !== null && !v.deadlines.some(x => x.status === "verified" && x.date === v.primaryDeadline
    && ["payment", "submission", "application", "acceptance", "response", "return"].includes(x.kind))) return false;
  if (v.primaryAmount !== null && !v.amounts.some(x => x.status === "verified" && x.value === v.primaryAmount
    && ["payment", "billed", "total", "outstanding"].includes(x.kind))) return false;
  return true;
}

export function isDocumentAnalysisResult(value: unknown): value is DocumentAnalysisResult {
  return isDocumentUploadResult(value) || isLegacyDocumentAnalysisResult(value);
}
