# Trusted Knowledge Strategy

## 1. Purpose

JapanxTheWorld uses trusted content first so known Japanese procedures are not answered like a generic AI chat. AI supports classification, fact extraction, and unknown-document fallback, but manually maintained JapanxTheWorld content is the primary source for known topics.

## 2. Why Trusted Content First

| Reason | Product impact |
| --- | --- |
| Procedures are sensitive | Users need cautious guidance, not confident guesses |
| Known topics repeat | Maintained templates can stay consistent across users |
| AI can overgeneralize | Trusted content reduces fabricated rules, deadlines, and outcomes |
| Backend can audit results | Topic IDs and template IDs make behavior easier to test |
| Frontend stays simple | All paths still return `DocumentAnalysisResult` |

This makes JapanxTheWorld different from a generic AI chatbot: it behaves like a guided support product with reviewed knowledge and AI fallback, not like an open-ended answer generator.

## 3. Routing Strategy

```txt
user input or document
-> normalize text
-> classify document template and trusted topic
-> if strong template match, return trusted template result
-> else if strong topic match, return trusted topic result
-> else use AI fallback explanation
-> validate DocumentAnalysisResult
-> return to frontend
```

## 4. Matching Rules

| Rule | Requirement |
| --- | --- |
| Use topic IDs | Route by stable IDs, not display text |
| Use aliases | Support English, Japanese, and mixed wording |
| Use keywords | Match document terms after normalization |
| Use strong keywords | Route to templates only when evidence is clear |
| Use confidence | Avoid trusted routing when confidence is weak |
| Detect conflicts | Lower confidence when unrelated topics both match |
| Avoid exact sentences | Do not depend on one hardcoded phrase |

### Bad matching example

```ts
if (input === "国民健康保険について知りたい") {
  return "national-health-insurance";
}
```

### Preferred matching inputs

| Input source | Example |
| --- | --- |
| Topic aliases | `health insurance`, `NHI`, `国民健康保険` |
| Keywords | `保険料`, `納期限`, `保険課` |
| Strong template terms | `国民健康保険料`, `納付書` |
| Classification result | `topicId`, `documentTemplateId`, `confidence` |

## 5. Confidence Guidance

| Confidence range | Suggested backend behavior |
| --- | --- |
| `0.85 - 1.0` | Use trusted document template if strong template keywords match |
| `0.65 - 0.84` | Use trusted topic content if topic evidence is strong |
| `0.40 - 0.64` | Use cautious topic-aware AI fallback or ask for confirmation |
| `0.00 - 0.39` | Use unknown-document AI fallback |

Confidence should drop when the document is damaged, contains unrelated lookalike terms, or has conflicting keywords such as tax and pension with no clear purpose.

## 6. AI Fallback Strategy

| Case | AI may do |
| --- | --- |
| Unknown document | Explain likely purpose cautiously |
| Unclear document | State that the document is unclear and recommend official confirmation |
| Known topic classification | Return classification metadata for backend routing |
| Fact extraction | Extract clearly present deadline, sender, amount, or requested action |

AI must not freely regenerate trusted procedural content for high-confidence known topics.

## 7. Official Source Requirements

| Requirement | Rule |
| --- | --- |
| Verified sources | Add official source URLs only after they are checked |
| Unverified content | Mark as TODO or keep `officialSources` empty |
| Sensitive procedures | Always set `needsOfficialConfirmation: true` |
| Legal or immigration topics | Never present content as final advice |
| Deadlines | Never invent dates or use ambiguous dates as deadlines |

## 8. `lastReviewedAt` Policy

| Policy | Requirement |
| --- | --- |
| Format | Use `YYYY-MM-DD` |
| Initial framework entries | Use the date the framework entry was created |
| Production-ready content | Update date after official-source review |
| Stale content | Mark for review before use in production |
| Major procedure change | Update content and review date together |

## 9. Content Review Process

| Step | Owner | Output |
| --- | --- | --- |
| Draft trusted topic | Frontend + AI behavior owner | Structured content entry |
| Verify official sources | Backend/content owner or project team | Source URLs and notes |
| Safety review | Project team | Warnings and official confirmation text |
| Backend routing update | Backend owner | Template/topic classifier behavior |
| Frontend display check | Frontend owner | Same `DocumentAnalysisResult` rendering |

## 10. Adding A New Trusted Topic

| Step | Requirement |
| --- | --- |
| 1 | Add stable `id`, English title, and Japanese title |
| 2 | Choose one category from the `TrustedTopic` category union |
| 3 | Add aliases and keywords for classification |
| 4 | Write summary, important points, and next steps in simple English |
| 5 | Keep factual rules cautious until verified |
| 6 | Add official sources only after verification |
| 7 | Set `needsOfficialConfirmation: true` for sensitive procedures |
| 8 | Add or update AI test cases for classification |

## 11. Deprecating Outdated Content

| Case | Action |
| --- | --- |
| Official source changes | Update content and `lastReviewedAt` |
| Content cannot be verified | Remove from trusted routing or mark as TODO |
| Topic becomes risky or outdated | Route to cautious AI fallback or official-support message |
| Template is ambiguous | Lower confidence threshold or remove template routing |

## 12. Responsibility Boundaries

| Area | Frontend / AI behavior owner | Backend owner |
| --- | --- | --- |
| `DocumentAnalysisResult` display | Owns | Consumes contract |
| Trusted topic content framework | Owns draft structure | May store and serve later |
| AI prompt behavior | Owns rules and examples | Implements provider call |
| Topic/template router | Documents expected behavior | Owns implementation |
| Database and auth | Out of scope | Owns |
| File handling and OCR | Out of scope | Owns |
| API validation | Specifies expectation | Owns implementation |

## 13. Frontend Result Transparency

| Source | Label | Helper text |
| --- | --- | --- |
| `template` | `Verified Guide` | `Based on JapanxTheWorld trusted content` |
| `ai` | `AI-assisted Explanation` | `Please confirm important details with official sources` |

This is a small future UI enhancement. The current result page should keep one shared layout.
