# JapanxTheWorld UI State And Error Handling

## 1. Standard UI State Model

```ts
type UiStatus = "idle" | "loading" | "success" | "empty" | "error";
```

## 2. Shared State Rules

| State | Meaning | UI behavior |
| --- | --- | --- |
| `idle` | No request has started yet | Show default screen or form |
| `loading` | Waiting for data or submit result | Show spinner, skeleton, or disabled controls |
| `success` | Data loaded or action completed | Show normal content |
| `empty` | Request succeeded but no useful records exist | Show friendly empty state with CTA |
| `error` | Request failed or data is invalid | Show error message and recovery action |

## 3. Copy Style Rules

| Rule | Requirement |
| --- | --- |
| Tone | Calm, simple, supportive |
| Length | 1 to 2 short sentences |
| Blame | Never blame the user |
| Recovery | Always say what the user can do next |
| Safety | When needed, remind the user to confirm with official sources |

## 4. Page State Matrix

| Page | Idle | Loading | Empty | Error |
| --- | --- | --- | --- | --- |
| Document Decoder | Show form and privacy note | Disable submit and show analyzing message | Not applicable | Inline validation or analysis failure |
| Document Result | Waiting for result or redirect fallback | Skeleton result card | Missing result message | Retry or return-to-decoder action |
| Life Guides | Optional intro | Card skeleton grid | No guides message | Retry banner |
| Guide Detail | Optional placeholder | Detail skeleton | Guide not found | Retry banner |
| Dashboard | Existing or default tasks | Optional loading row | Encourage first task | Dashboard error block |
| Help Center | Optional intro | Resource skeleton cards | No resources message | Retry banner |

## 5. Validation Rules

| Input area | Validation rule | Failure UI |
| --- | --- | --- |
| Document text | Required unless supported upload flow exists | Inline message below textarea |
| Document type hint | Optional | No blocking error |
| Checklist title | Required | Inline form error |
| Checklist due date | Optional but must be a valid date if entered | Inline form error |
| Checklist category | Required in create/edit flows | Inline form error |

## 6. Loading UI Patterns

| Pattern | Use when | Notes |
| --- | --- | --- |
| Button spinner | Form submission | Keep label readable, for example “Analyzing...” |
| Card skeleton | Guide/resource loading | Match final card size to reduce layout shift |
| Section placeholder | Result page loading | Use 3 to 5 placeholder blocks |
| Row saving state | Checklist update/delete | Only affect the target item |

## 7. Error Handling Rules

| Rule | Requirement |
| --- | --- |
| Retry support | Show retry action for recoverable fetch failures |
| Input preservation | Keep user input after submit failure when possible |
| Granularity | Use item-level feedback for checklist mutations |
| Logging | Console-log raw invalid response details in development only |
| Fallback | If backend is unavailable in development, allow mock fallback where configured |

## 8. Special Cases

### Document analysis timeout

| Item | Requirement |
| --- | --- |
| Trigger | Analysis request takes too long or backend timeout |
| User message | “The analysis took too long. Please try again with clearer text.” |
| Recovery | Retry button and preserved text input |

### Unreadable file or text

| Item | Requirement |
| --- | --- |
| Trigger | OCR/backend cannot identify useful text |
| User message | “We could not read enough text from this document. Please try clearer text or a better image.” |
| Recovery | Return to input form |

### Unknown document type

| Item | Requirement |
| --- | --- |
| Trigger | Backend cannot match a trusted template |
| User message | Show normal result layout with cautious wording |
| Recovery | Encourage official confirmation |

### Missing deadline

| Item | Requirement |
| --- | --- |
| Trigger | `deadline` is `null` |
| User message | “No clear deadline was found in this result.” |
| Recovery | Keep guidance focused on checking with official sources |

### Failed official-links fetch

| Item | Requirement |
| --- | --- |
| Trigger | `GET /api/resources` fails |
| User message | “Support links could not be loaded right now.” |
| Recovery | Retry action |

## 9. Example Error Copy

| Scenario | Suggested copy |
| --- | --- |
| Generic request failure | “Something went wrong while loading this information. Please try again.” |
| Decoder validation | “Please paste document text before starting analysis.” |
| Invalid result format | “The analysis result could not be displayed safely. Please try again.” |
| Checklist save failure | “Your task could not be saved. Please try again.” |
| Checklist delete failure | “This task could not be deleted right now. Please try again.” |

## 10. Checklist Mutation Feedback

| Action | Success feedback | Error feedback |
| --- | --- | --- |
| Create item | New row appears immediately | Inline form message |
| Toggle complete | Visual state updates | Revert row state and show inline error |
| Edit item | Row text updates | Keep edit mode or revert and show message |
| Delete item | Row disappears | Restore row and show inline error |

## 11. Acceptance Checklist

| Check | Requirement |
| --- | --- |
| Coverage | Every main feature has loading, empty, and error rules where relevant |
| Reuse | Shared UI states use similar styling and wording |
| Safety | Decoder warnings remain visible even on uncertain output |
| DX | Mock mode can simulate async loading and errors during development |
