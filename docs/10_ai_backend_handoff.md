# AI Document Decoder Backend Handoff

## 1. Endpoint

| Item | Requirement |
| --- | --- |
| Endpoint | `POST /api/documents/analyze` |
| Owner | Backend teammate |
| Frontend status | Ready to call through `src/api/client.ts` |
| Backend implementation | Out of scope for frontend |
| Initial behavior | Manual template when known; AI explanation when unknown |

## 1.1 Future Decoder Flow

```txt
input
-> normalization
-> template/topic classification
-> trusted match OR AI fallback
-> response validation
-> DocumentAnalysisResult
-> frontend
```

The backend owns this router implementation. The frontend only expects a valid `DocumentAnalysisResult` on success.

## 2. Frontend Request Shape

```ts
export type DocumentFileInput = {
  file: File;
  name: string;
  type: string;
  size: number;
};

export type DocumentAnalysisRequest = {
  documentText?: string;
  documentFile?: DocumentFileInput;
  documentTypeHint?: string;
  sourceLanguageHint?: string;
};
```

### Input rules

| Rule | Requirement |
| --- | --- |
| Minimum input | Accept either pasted text, one uploaded file, or both |
| Empty input | Return `400` with `ApiError.code = "EMPTY_DOCUMENT"` |
| Supported upload types | JPEG, PNG, WebP, and PDF |
| Frontend upload limit | 10 MB |
| Mock-mode behavior | Frontend can submit selected files for UI testing, but no OCR is performed |
| Production file behavior | Backend extracts readable text from the uploaded file before classification |

### Example text-only request

```json
{
  "documentText": "国民健康保険料のお知らせです。2026年8月10日までにお支払いください。",
  "documentTypeHint": "insurance notice",
  "sourceLanguageHint": "ja"
}
```

### Example file request

```txt
POST /api/documents/analyze
Content-Type: multipart/form-data

file: kokumin-kenko-hoken-notice.webp
documentText: optional pasted text that should be analyzed together with the file
documentTypeHint: insurance notice
sourceLanguageHint: ja
```

### Backend file/OCR expectations

| Case | Backend action |
| --- | --- |
| Image/PDF has readable text | Extract text, classify document/topic, then return `DocumentAnalysisResult` |
| Image/PDF cannot be read | Return `422` with `ApiError.code = "UNREADABLE_DOCUMENT"` |
| File type is unsupported | Return `415` or `422` with `ApiError.code = "UNSUPPORTED_FILE_TYPE"` |
| File is too large | Return `413` with `ApiError.code = "FILE_TOO_LARGE"` |
| Text and file are both provided | Prefer combined analysis; do not ignore pasted text |

## 3. Required Response Shape

```ts
export type DocumentAnalysisResult = {
  source: "template" | "ai";
  documentType: string;
  summary: string;
  deadline: string | null;
  urgency: "low" | "important" | "urgent";
  importantPoints: string[];
  nextSteps: string[];
  relatedGuide: string | null;
  officialWarning: string;
};
```

### Required response rules

| Field | Backend rule |
| --- | --- |
| `source` | `"template"` for manual trusted result, `"ai"` for generated result |
| `deadline` | `YYYY-MM-DD` only when clearly present, otherwise `null` |
| `urgency` | Must be one of `low`, `important`, or `urgent` |
| `importantPoints` | Array of short simple-English facts |
| `nextSteps` | Array of short practical user actions |
| `relatedGuide` | Existing guide ID or `null` |
| `officialWarning` | Always non-empty |

## 4. Manual Template Vs AI Behavior

| Input classification | Backend behavior | Response source |
| --- | --- | --- |
| Known, high-confidence template category | Return reviewed manual result, optionally filling clear deadline from input | `template` |
| Known trusted topic but no exact template | Adapt trusted topic content into the shared result shape | `template` |
| Unknown category | Run AI prompt v1 and validate result | `ai` |
| Unclear text | Return cautious AI result or safe fallback result | `ai` |

## 4.1 Classification Schema

```ts
export type TopicClassificationResult = {
  topicId: string | null;
  documentTemplateId: string | null;
  confidence: number;
  reason?: string;
};
```

| Field | Backend use |
| --- | --- |
| `topicId` | Select trusted topic content when confidence is strong |
| `documentTemplateId` | Select trusted document template when confidence is strong |
| `confidence` | Decide trusted template, trusted topic, or AI fallback |
| `reason` | Optional internal explanation for testing and debugging |

## 4.2 Matching Strategy

Avoid exact string matching such as one hardcoded sentence. User input and documents will vary too much.

| Signal | Recommended use |
| --- | --- |
| Normalized keywords | Match Japanese and English terms after whitespace/case normalization |
| Aliases | Capture natural user wording such as `resident tax`, `NHI`, or `visa renewal` |
| Strong keywords | Route confidently to a document template |
| Topic IDs | Keep routing stable even when display titles change |
| Conflict checks | Lower confidence when multiple unrelated topics match |

## 5. Initial Known Template Categories

| Category | Template asset in frontend |
| --- | --- |
| National Health Insurance | `documentTemplateResults.nationalHealthInsurance` |
| National Pension | `documentTemplateResults.nationalPension` |
| Residence Tax | `documentTemplateResults.residenceTax` |
| Address Registration | `documentTemplateResults.addressRegistration` |
| Immigration / Residence Status | `documentTemplateResults.immigrationResidenceStatus` |
| School Administrative / Payment | `documentTemplateResults.schoolAdministrativePayment` |
| Employment / Working Conditions | `documentTemplateResults.employmentWorkingConditions` |
| General City Hall | `documentTemplateResults.generalCityHall` |

## 6. API Failure Behavior

| Failure | Preferred backend response |
| --- | --- |
| Empty input | `400` with `ApiError.code = "EMPTY_DOCUMENT"` |
| Unsupported file type | `415` or `422` with `ApiError.code = "UNSUPPORTED_FILE_TYPE"` |
| File too large | `413` with `ApiError.code = "FILE_TOO_LARGE"` |
| Unsupported file or unreadable text | `422` with `ApiError.code = "UNREADABLE_DOCUMENT"` |
| AI provider timeout | `504` with `ApiError.code = "ANALYSIS_TIMEOUT"` |
| AI provider unavailable | `503` with `ApiError.code = "ANALYSIS_UNAVAILABLE"` |
| Malformed AI output | `502` with `ApiError.code = "MALFORMED_ANALYSIS"` |

### Error shape

```ts
export type ApiError = {
  code: string;
  message: string;
  details?: string[];
};
```

## 7. Timeout Behavior

| Area | Requirement |
| --- | --- |
| Backend timeout | Use a clear timeout for AI provider calls |
| Frontend expectation | Frontend shows an error and keeps user input when possible |
| Retry | User can retry from the same page |
| Partial result | Do not return partial malformed success JSON |

## 8. Malformed AI Output Behavior

| Step | Requirement |
| --- | --- |
| 1 | Validate AI output is parseable JSON |
| 2 | Validate exactly the required fields exist |
| 3 | Validate enum values and deadline format |
| 4 | Reject extra fields or missing fields |
| 5 | Return `ApiError` if a valid `DocumentAnalysisResult` cannot be produced |

## 9. Fallback Requirements

| Case | Fallback |
| --- | --- |
| Unknown but readable document | Return cautious AI result |
| Unclear document | Use `documentType: "Unknown Official Document"`, `deadline: null`, and `urgency: "important"` |
| Known category with missing deadline | Return template-style result with `deadline: null` |
| Related guide uncertain | Return `relatedGuide: null` |

## 9.1 Trusted Topic Fallback

When classification finds a known topic but no exact document template, the backend may use `trustedTopics` to produce a `source: "template"` result.

| Trusted topic field | Maps to `DocumentAnalysisResult` |
| --- | --- |
| `title` | `documentType` |
| `summary` | `summary` |
| `importantPoints` | `importantPoints` |
| `nextSteps` | `nextSteps` |
| `needsOfficialConfirmation` and `warnings` | `officialWarning` |

The backend should still extract a clearly present deadline when available. It must keep `deadline: null` when no clear deadline is present.

## 10. Privacy Expectations

| Requirement | Detail |
| --- | --- |
| Minimize storage | Do not store document text unless required and clearly agreed |
| Avoid sensitive logs | Do not log raw personal document text in production logs |
| Redaction | Remove or mask personal identifiers before long-term debugging storage |
| User warning | Frontend already shows privacy warning before analysis |
| Data ownership | Backend owner should define retention, deletion, and access policy |

## 11. What The Frontend Expects

| Frontend behavior | Backend requirement |
| --- | --- |
| One result page for all outputs | Always return `DocumentAnalysisResult` on success |
| Same UI for template and AI | Do not require frontend to branch on `source` |
| Deadline display | Return `null` when no clear deadline exists |
| Warning block | Always include `officialWarning` |
| Related guide button | Return guide ID only when it exists in frontend routes |
| Error UI | Return `ApiError` for failures |

## 12. Ready-To-Test Assets

| File | Purpose |
| --- | --- |
| `src/data/aiTestCases.ts` | Synthetic test inputs and expected checks |
| `src/data/documentTemplates.ts` | Manual template result examples |
| `docs/09_ai_evaluation_plan.md` | Pass/fail evaluation process |
| `docs/04_ai_document_decoder_spec.md` | Production-style prompt and AI rules |
| `docs/11_trusted_knowledge_strategy.md` | Trusted knowledge first architecture and maintenance rules |
