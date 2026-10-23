import type { DocumentUploadResult, ExtractedField, SourceEvidence } from "../types";

export const field = (label: string, kind: string, evidenceId: string): ExtractedField => ({
  label, kind, status: "verified", reasons: [], evidenceIds: [evidenceId],
  ocrConfidence: .99, association: "text_and_geometry", occurrences: 1,
});
const source = (text: string, index: number): SourceEvidence => ({
  id: `p1-b${index}`, text, confidence: .99, bbox: [0, index * 80, 300, index * 80 + 20],
  polygon: null, page: 1, originalIndex: index, readingOrder: index, extractionMethod: "paddleocr",
});

/** Synthetic data with the exact Step 7 schema; contains no real document data. */
export function uploadResult(overrides: Partial<DocumentUploadResult> = {}): DocumentUploadResult {
  return {
    source: "deterministic", extractionMethod: "paddleocr",
    documentType: "National Health Insurance Tax", summary: "Payment amount: JPY 18,000.",
    deadline: "2026-11-02", primaryDeadline: "2026-11-02", primaryAmount: null,
    urgency: null, relatedGuide: null, officialWarning: "Some fields are unverified; check their source evidence.",
    deadlines: [
      { ...field("Payment deadline", "payment", "p1-b1"), date: "2026-11-02" },
      { ...field("Usage expiration date", "usage_expiration", "p1-b2"), date: "2027-11-02" },
    ],
    amounts: [
      { ...field("Payment amount", "payment", "p1-b3"), value: 18000, currency: "JPY", occurrences: 3 },
      { ...field("Total amount", "total", "p1-b4"), value: null, currency: "JPY", status: "unverified", reasons: ["No readable monetary value is associated with this label."] },
    ],
    evidence: [source("国民健康保険税", 0), source("納期限 令和8年11月2日", 1), source("利用期限 令和9年11月2日", 2),
      source("納付額 18,000円", 3), source("合計金額", 4), source("UNRELATED_PRIVATE_ADDRESS 12345678901234567890", 5)],
    extractionStatus: "partial", warnings: ["Some fields are unverified; check their source evidence."],
    importantPoints: ["Payment deadline: 2026-11-02."], nextSteps: ["Verify the unverified fields against the original document."],
    documentTypeEvidenceIds: ["p1-b0"], completedPaymentEvidenceIds: [],
    pages: [{ page: 1, method: "paddleocr", coordinateSystem: "image_pixels", width: 1000, height: 1200, auxiliaryFramesSkipped: 0 }],
    ...overrides,
  };
}
