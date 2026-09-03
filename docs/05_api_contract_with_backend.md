# JapanxTheWorld API Contract With Backend

## 1. Shared API Rules

| Item | Decision |
| --- | --- |
| Base path | `/api` |
| Response format | JSON |
| Frontend HTTP layer | `fetch` through `src/api/client.ts` |
| Initial mode | Mock data first |
| Auth | Out of scope for v1 docs, leave optional header support only |
| Error shape | Shared `ApiError` object |

## 2. Shared TypeScript Types

```ts
export type ApiError = {
  code: string;
  message: string;
  details?: string[];
};

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

export type GuideSummary = {
  id: string;
  title: string;
  category: string;
  summary: string;
  estimatedReadMinutes: number;
};

export type GuideDetail = GuideSummary & {
  audience: string;
  requiredDocuments: string[];
  steps: string[];
  officialResourceIds: string[];
};

export type OfficialResource = {
  id: string;
  title: string;
  category: string;
  description: string;
  url: string;
};

export type ChecklistItem = {
  id: string;
  title: string;
  completed: boolean;
  dueDate: string | null;
  category: string;
};

export type ChecklistCreateInput = {
  title: string;
  dueDate?: string | null;
  category: string;
};

export type ChecklistUpdateInput = Partial<ChecklistCreateInput> & {
  completed?: boolean;
};
```

## 3. Error Response Shape

```json
{
  "code": "ANALYSIS_TIMEOUT",
  "message": "The document analysis took too long.",
  "details": [
    "Please try again with clearer text."
  ]
}
```

## 4. Endpoint Specs

### `POST /api/documents/analyze`

| Item | Spec |
| --- | --- |
| Purpose | Analyze user-provided document text, uploaded photo/image, or PDF and return a shared result shape |
| Request type | `DocumentAnalysisRequest` |
| Success type | `DocumentAnalysisResult` |
| Loading state | Disable submit, show spinner and “Analyzing document...” |
| Success state | Navigate to result page and render returned object |
| Error state | Show retry block and keep previous input visible |

#### Request input rules

| Rule | Requirement |
| --- | --- |
| Minimum input | At least one of `documentText` or `documentFile` is required |
| Text-only request | Send JSON with `documentText`, `documentTypeHint`, and `sourceLanguageHint` |
| File request | Send `multipart/form-data` with `file` plus optional `documentText`, `documentTypeHint`, and `sourceLanguageHint` |
| Supported file types | `image/jpeg`, `image/png`, `image/webp`, `application/pdf` |
| Frontend max size | 10 MB |
| OCR ownership | Backend owns OCR/file extraction and should return `UNREADABLE_DOCUMENT` when text cannot be extracted safely |

#### Example text-only request

```json
{
  "documentText": "Japanese document text here",
  "documentTypeHint": "tax notice",
  "sourceLanguageHint": "ja"
}
```

#### Example file request fields

```txt
Content-Type: multipart/form-data

file: residence-tax-notice.pdf
documentText: optional pasted text
documentTypeHint: tax notice
sourceLanguageHint: ja
```

#### Example success

```json
{
  "source": "template",
  "documentType": "Residence Tax Notice",
  "summary": "This document explains your residence tax amount and payment schedule.",
  "deadline": "2026-07-31",
  "urgency": "important",
  "importantPoints": [
    "Check the total payment amount.",
    "Look for the due date.",
    "Keep the notice for your records."
  ],
  "nextSteps": [
    "Confirm the payment deadline.",
    "Review official payment options.",
    "Ask official support if anything is unclear."
  ],
  "relatedGuide": "residence-tax-payment",
  "officialWarning": "Please confirm important tax procedures with your city office or official government sources."
}
```

### `GET /api/guides`

| Item | Spec |
| --- | --- |
| Purpose | Fetch the list of available life guides |
| Request body | None |
| Success type | `GuideSummary[]` |
| Loading state | Render guide card skeletons |
| Success state | Show guide card grid |
| Error state | Show banner with retry action |

#### Example success

```json
[
  {
    "id": "moving-address-registration",
    "title": "Address Registration After Moving",
    "category": "City Hall",
    "summary": "What to do after moving to a new address in Japan.",
    "estimatedReadMinutes": 5
  }
]
```

### `GET /api/guides/:id`

| Item | Spec |
| --- | --- |
| Purpose | Fetch one full guide detail |
| Request body | None |
| Success type | `GuideDetail` |
| Loading state | Show detail skeleton |
| Success state | Render guide details and linked resources |
| Error state | Show not-found or fetch error block |

#### Example success

```json
{
  "id": "moving-address-registration",
  "title": "Address Registration After Moving",
  "category": "City Hall",
  "summary": "What to do after moving to a new address in Japan.",
  "estimatedReadMinutes": 5,
  "audience": "Students and workers who changed residence",
  "requiredDocuments": [
    "Residence card",
    "My Number card if available"
  ],
  "steps": [
    "Visit your city office soon after moving.",
    "Bring your residence card and related documents.",
    "Complete the address registration form."
  ],
  "officialResourceIds": [
    "city-hall-moving-guide"
  ]
}
```

### `GET /api/resources`

| Item | Spec |
| --- | --- |
| Purpose | Fetch official support links and help resources |
| Request body | None |
| Success type | `OfficialResource[]` |
| Loading state | Show resource card skeletons |
| Success state | Show resource list or grouped cards |
| Error state | Show retry banner |

#### Example success

```json
[
  {
    "id": "immigration-main",
    "title": "Immigration Services Agency of Japan",
    "category": "Immigration",
    "description": "Official immigration procedures and notices.",
    "url": "https://www.moj.go.jp/isa/"
  }
]
```

### `GET /api/checklist`

| Item | Spec |
| --- | --- |
| Purpose | Fetch current checklist items |
| Request body | None |
| Success type | `ChecklistItem[]` |
| Loading state | Show loading message or skeleton rows |
| Success state | Show dashboard tasks and completion summary |
| Error state | Show dashboard fetch error block |

#### Example success

```json
[
  {
    "id": "task-1",
    "title": "Pay health insurance notice",
    "completed": false,
    "dueDate": "2026-08-10",
    "category": "Insurance"
  }
]
```

### `POST /api/checklist`

| Item | Spec |
| --- | --- |
| Purpose | Create a new checklist item |
| Request type | `ChecklistCreateInput` |
| Success type | `ChecklistItem` |
| Loading state | Disable form submit and show saving state |
| Success state | Append new item to dashboard list |
| Error state | Show inline save error and preserve form input |

#### Example request

```json
{
  "title": "Visit city office about address change",
  "dueDate": "2026-07-05",
  "category": "City Hall"
}
```

#### Example success

```json
{
  "id": "task-2",
  "title": "Visit city office about address change",
  "completed": false,
  "dueDate": "2026-07-05",
  "category": "City Hall"
}
```

### `PATCH /api/checklist/:id`

| Item | Spec |
| --- | --- |
| Purpose | Update checklist completion or content |
| Request type | `ChecklistUpdateInput` |
| Success type | `ChecklistItem` |
| Loading state | Show item-level saving state |
| Success state | Replace item in local list |
| Error state | Revert optimistic UI or show inline error |

#### Example request

```json
{
  "completed": true
}
```

#### Example success

```json
{
  "id": "task-2",
  "title": "Visit city office about address change",
  "completed": true,
  "dueDate": "2026-07-05",
  "category": "City Hall"
}
```

### `DELETE /api/checklist/:id`

| Item | Spec |
| --- | --- |
| Purpose | Delete a checklist item |
| Request body | None |
| Success type | `{ "success": true, "id": string }` |
| Loading state | Disable delete button for the target row |
| Success state | Remove row from local dashboard list |
| Error state | Restore row and show inline error |

#### Example success

```json
{
  "success": true,
  "id": "task-2"
}
```

## 5. Frontend Integration Notes

| Topic | Contract |
| --- | --- |
| Mock mode | Client helpers may return `Promise.resolve(mockData)` initially |
| Headers | Support optional `headers` config for future auth |
| Error handling | Non-2xx responses should map to `ApiError` |
| Parsing | Frontend should validate critical fields before rendering |
| Checklist UX | Item-level updates are preferred for better feedback |

## 6. Handoff Checklist For Backend Owner

| Check | Requirement |
| --- | --- |
| Naming | Use the exact field names shown in this file |
| Dates | Return date strings or `null`, never partial objects |
| Decoder output | Keep one shared result shape for template and AI sources |
| Empty collections | Return `[]` instead of `null` for list endpoints |
| Errors | Return `ApiError`-style JSON on failure |
