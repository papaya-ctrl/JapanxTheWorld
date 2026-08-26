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

## 14. Initial Supported Document Categories

The backend should start with trusted templates or strong classification rules for these categories.

| Category | Preferred `documentType` label | Result source guidance |
| --- | --- | --- |
| National Health Insurance notice | `National Health Insurance Notice` | Use template when payment or enrollment notice is clear |
| National Pension notice | `National Pension Notice` | Use template when pension payment or exemption wording is clear |
| Residence Tax notice | `Residence Tax Notice` | Use template when residence tax wording is clear |
| Address registration / moving notice | `Address Registration Notice` | Use template for moving-in, moving-out, or address update notices |
| Immigration / residence-status notice | `Immigration / Residence Status Notice` | Use template only for safe procedural explanation |
| School payment or administrative notice | `School Administrative Notice` | Use AI unless a school template is maintained |
| Employment contract / working conditions notice | `Employment / Working Conditions Notice` | Use AI or reviewed template; never decide legality |
| Part-time work related notice | `Part-Time Work Notice` | Use AI or reviewed template; mention official confirmation |
| City hall general administrative notice | `City Hall Administrative Notice` | Use AI unless known city hall template matches |
| Unknown/general official Japanese document | `Unknown Official Document` | Use AI with cautious wording |

## 15. AI Prompt V1

```txt
You are the AI document explanation layer for JapanxTheWorld.

Audience:
Foreign students and workers in Japan who need simple English support for Japanese documents.

Task:
Read the provided Japanese document text and return one JSON object that matches the schema exactly.

Required behavior:
- Identify the likely document type.
- Give a short simple-English summary.
- Extract a deadline only if it is clearly written.
- Convert clearly written Japanese dates, including Reiwa era dates, to YYYY-MM-DD.
- If no clear deadline exists, use null.
- Assign urgency as "low", "important", or "urgent".
- Provide practical importantPoints and nextSteps.
- Suggest relatedGuide only when there is a clearly relevant guide ID.
- Always include officialWarning.

Safety rules:
- Use simple English suitable for non-native English speakers.
- Do not provide Easy Japanese.
- Do not provide vocabulary lessons.
- Never claim that visa or residence-status approval is guaranteed.
- Never give final legal, immigration, tax, medical, financial, or government-authority decisions.
- Clearly separate facts found in the document from suggested next actions.
- Never invent a deadline, amount, sender, approval result, or penalty.
- If the document is unclear, say that it is unclear, set urgency to "important", and recommend official confirmation.
- Important procedures must recommend confirmation with the issuing organization or an official source.

Output rules:
- Return JSON only.
- Do not wrap the JSON in Markdown.
- Do not include extra fields.
- Do not omit required fields.
- Use this exact schema:

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

Allowed relatedGuide values:
- "health-insurance-payment"
- "residence-tax-payment"
- "moving-address-registration"
- "job-hunting-before-graduation"
- null

Input:
documentText:
{{documentText}}

optionalDocumentTypeHint:
{{documentTypeHint}}
```

## 16. Deadline And Urgency Rules

| Case | Deadline output | Urgency output |
| --- | --- | --- |
| Clear ISO or Japanese date exists | Convert to `YYYY-MM-DD` | `important` or `urgent` depending on timing and wording |
| Clear Reiwa era date exists | Convert to Gregorian `YYYY-MM-DD` | `important` or `urgent` depending on timing and wording |
| Payment due date exists | Extract exact date | Usually `important`; use `urgent` for final notice or immediate action |
| Information-only notice | `null` unless a deadline is written | Usually `low` |
| Unclear document | `null` unless a deadline is unmistakable | `important` |
| Ambiguous wording | `null` unless date purpose is clear | `important` |

## 17. Schema Compliance Checklist

| Check | Pass condition |
| --- | --- |
| Required keys | All 9 keys are present |
| Extra keys | No extra keys are returned |
| `source` | Must be `"template"` or `"ai"` |
| `deadline` | Must be `YYYY-MM-DD` or `null` |
| `urgency` | Must be `"low"`, `"important"`, or `"urgent"` |
| Arrays | `importantPoints` and `nextSteps` are arrays of short strings |
| Warning | `officialWarning` is always non-empty |

## 18. Trusted Knowledge First Rule

JapanxTheWorld must not behave like a generic chatbot for known procedures. The backend should use trusted manually maintained content before AI-generated procedural content.

| Layer | Behavior | Result source |
| --- | --- | --- |
| 1. Known document/template match | Return reviewed manual template content and only extract clearly present facts such as deadline | `template` |
| 2. Known topic/intent match | Return trusted topic content adapted into `DocumentAnalysisResult` | `template` |
| 3. Unknown or low-confidence input | Use AI fallback explanation with cautious wording | `ai` |

## 19. Limited AI Responsibilities

| AI responsibility | Allowed | Not allowed |
| --- | --- | --- |
| Classification | Identify likely topic ID or document template ID | Replace trusted content for high-confidence known topics |
| Fact extraction | Extract clearly present facts such as deadline, sender, document type, and requested action | Invent missing deadlines, amounts, policy rules, or outcomes |
| Fallback explanation | Explain unknown or unmatched documents cautiously | Give final legal, immigration, tax, medical, financial, or authority decisions |

For known topics, AI should identify the topic and return classification metadata to the backend router. The router should select trusted manual content and produce the final `DocumentAnalysisResult`.

## 20. Topic Classification Schema

```ts
export type TopicClassificationResult = {
  topicId: string | null;
  documentTemplateId: string | null;
  confidence: number;
  reason?: string;
};
```

| Field | Rule |
| --- | --- |
| `topicId` | Known trusted topic ID or `null` |
| `documentTemplateId` | Known document template ID or `null` |
| `confidence` | Number from `0` to `1` |
| `reason` | Short explanation for backend logs or evaluation |

## 21. Matching Strategy Guidance

Do not use exact sentence matching such as:

```ts
if (input === "国民健康保険について知りたい") {
  // route to health insurance
}
```

Use normalized matching instead.

| Input signal | Use |
| --- | --- |
| Topic IDs | Stable internal routing target |
| Aliases | English and Japanese user wording variations |
| Keywords | Document terms and administrative words |
| Strong keywords | High-confidence phrases for known templates |
| Classification confidence | Decide trusted result, topic result, or AI fallback |
| Conflict detection | Lower confidence when multiple unrelated topics match |

## 22. Source Transparency UI Specification

This is a future UI enhancement only. Do not redesign the result page.

| Result source | Suggested label | Suggested helper text |
| --- | --- | --- |
| `template` | `Verified Guide` | `Based on JapanxTheWorld trusted content` |
| `ai` | `AI-assisted Explanation` | `Please confirm important details with official sources` |
