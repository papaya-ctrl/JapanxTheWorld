# JapanxTheWorld AI Document Decoder Specification

## 1. Feature Goal

The Document Decoder helps users understand Japanese documents through one frontend-facing result format. The backend may use either a trusted manual template or AI generation, but the frontend must render both in the same way.

## 2. Hybrid Result Strategy

| Case | Backend behavior | Frontend behavior |
| --- | --- | --- |
| Known document type | Return trusted template-based explanation | Render standard result card |
| Unknown document type | Return AI-generated explanation | Render standard result card |
| Unclear or low-confidence input | Return cautious result with confirmation warning | Render standard result card and emphasize warning |

## 3. Frontend Contract

```json
{
  "source": "template",
  "documentType": "Residence Tax Notice",
  "summary": "This document explains your residence tax amount and payment schedule.",
  "deadline": "2026-07-31",
  "urgency": "important",
  "importantPoints": [
    "Check the amount you need to pay.",
    "Look for the payment due date.",
    "Keep the notice for your records."
  ],
  "nextSteps": [
    "Confirm the payment deadline on the notice.",
    "Check your city office website for payment methods.",
    "Ask official support if you are unsure about the amount."
  ],
  "relatedGuide": "residence-tax-payment",
  "officialWarning": "Please confirm important tax procedures with your city office or official government sources."
}
```

## 4. Required JSON Schema

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `source` | `"template" \| "ai"` | Yes | Tells backend source only; frontend layout stays the same |
| `documentType` | `string` | Yes | Short English label for the document |
| `summary` | `string` | Yes | Simple English explanation |
| `deadline` | `string \| null` | Yes | ISO-style date string if known, otherwise `null` |
| `urgency` | `"low" \| "important" \| "urgent"` | Yes | Must reflect time sensitivity and confidence |
| `importantPoints` | `string[]` | Yes | 2 to 5 short points |
| `nextSteps` | `string[]` | Yes | 2 to 5 action-oriented steps |
| `relatedGuide` | `string \| null` | Yes | Guide ID if related guide exists |
| `officialWarning` | `string` | Yes | Always present |

## 5. AI Behavior Rules

| Rule | Requirement |
| --- | --- |
| Language | Use simple English |
| Safety | Do not give final legal, immigration, tax, medical, or financial advice |
| Confirmation | Always tell users to confirm important procedures with official sources |
| Missing deadline | Return `null` for `deadline` |
| Unclear document | Set `urgency` to `important` and ask user to confirm with official support |
| Vocabulary/Easy Japanese | Do not add vocabulary explanation or Easy Japanese output |
| Confidence handling | If details are uncertain, say so clearly in `summary` or `officialWarning` |

## 6. Prompt Template For Backend AI Layer

```txt
You are an assistant for foreign students and workers in Japan.

Task:
Explain the uploaded or pasted Japanese document in simple English.

Rules:
- Output valid JSON only.
- Use the exact schema provided.
- Do not include Easy Japanese.
- Do not include vocabulary explanations.
- Do not give final legal, immigration, tax, medical, or financial advice.
- Always encourage confirmation with official sources.
- If the deadline is not clear, return null for deadline.
- If the document is unclear or confidence is low, set urgency to "important".
- Keep summary short and calm.
- Keep importantPoints and nextSteps practical.

Schema:
{
  "source": "ai",
  "documentType": string,
  "summary": string,
  "deadline": string | null,
  "urgency": "low" | "important" | "urgent",
  "importantPoints": string[],
  "nextSteps": string[],
  "relatedGuide": string | null,
  "officialWarning": string
}

Input document text:
{{documentText}}

Optional hint:
{{documentTypeHint}}
```

## 7. Frontend TypeScript Types

```ts
export type AnalysisSource = "template" | "ai";

export type AnalysisUrgency = "low" | "important" | "urgent";

export type DocumentAnalysisResult = {
  source: AnalysisSource;
  documentType: string;
  summary: string;
  deadline: string | null;
  urgency: AnalysisUrgency;
  importantPoints: string[];
  nextSteps: string[];
  relatedGuide: string | null;
  officialWarning: string;
};

export type DocumentAnalysisRequest = {
  documentText: string;
  documentTypeHint?: string;
  sourceLanguageHint?: string;
};
```

## 8. Mock Result Examples

### Example A: Template Result

```json
{
  "source": "template",
  "documentType": "National Health Insurance Payment Notice",
  "summary": "This notice tells you the amount you need to pay for national health insurance.",
  "deadline": "2026-08-10",
  "urgency": "important",
  "importantPoints": [
    "The document includes a payment amount.",
    "There is a due date for payment.",
    "Late payment may cause problems."
  ],
  "nextSteps": [
    "Check the due date on the notice.",
    "Review official payment options from your city office.",
    "Ask your city office if you do not understand the notice."
  ],
  "relatedGuide": "health-insurance-payment",
  "officialWarning": "Please confirm health insurance payment details with your city office or official government sources."
}
```

### Example B: AI Result

```json
{
  "source": "ai",
  "documentType": "Unknown municipal notice",
  "summary": "This looks like a city office notice about a required response, but the exact purpose is not fully clear from the text provided.",
  "deadline": null,
  "urgency": "important",
  "importantPoints": [
    "The document appears to request action from you.",
    "The exact deadline is not clear.",
    "You should verify the purpose with official support."
  ],
  "nextSteps": [
    "Check the sender name and contact information on the document.",
    "Contact the city office or listed support desk.",
    "Bring the document to official support if you need confirmation."
  ],
  "relatedGuide": null,
  "officialWarning": "This result may be incomplete. Please confirm the document meaning and any deadlines with the official sender."
}
```

## 9. UI Rendering Rules

| UI area | Rendering rule |
| --- | --- |
| Source label | Optional small label may show `template` or `ai`, but not as the main content focus |
| Summary | Show near top in readable paragraph form |
| Deadline | Show a date block only when not `null` |
| Urgency | Always render through `UrgencyBadge` |
| Important points | Render as short list items |
| Next steps | Render as ordered action list |
| Warning | Always render as a highlighted caution block |

## 10. Error States

| Error case | Frontend handling |
| --- | --- |
| Empty input | Block submission and show inline validation |
| API timeout | Show retry message and keep user input if possible |
| Invalid JSON | Show generic analysis error and log for debugging |
| Missing required fields | Treat response as invalid and show fallback error |
| Unreadable text | Show message asking the user to paste clearer text or retry |
| Unsupported file in v1 | Show file limitation note and keep text input as primary path |

## 11. Privacy Warning Text

```txt
Do not upload highly sensitive personal information unless you understand how the service will process it. If your document includes private details, confirm whether it is safe to share before submitting.
```

## 12. Official Confirmation Warning Text

```txt
This explanation is only a support tool. For immigration, tax, insurance, legal, medical, financial, or deadline-related decisions, please confirm the document with the official organization or a trusted support desk.
```

## 13. Frontend Acceptance Checklist

| Check | Requirement |
| --- | --- |
| Contract stability | Frontend works the same for `source: "template"` and `source: "ai"` |
| Safety | Warnings are always visible |
| Clarity | No vocabulary mode or Easy Japanese content appears |
| Missing deadline | UI handles `deadline: null` gracefully |
| Unclear results | `important` urgency is shown clearly for uncertain documents |
