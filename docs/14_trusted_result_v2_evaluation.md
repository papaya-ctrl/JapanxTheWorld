# Trusted Result Generation V2 Evaluation

## Dataset

The evaluation uses 54 synthetic cases from `src/data/aiTestCases.ts`; it contains no real personal data.

- 40 cases cover the eight Manual Trusted Content V1 topics, with strong, alternative-term, short-but-sufficient, no-deadline, and explicit-deadline variants for each topic.
- 12 cases cover ambiguous payments, unrelated school/general text, generic insurance/tax wording, conflicting topics, malformed input, and negated trusted wording.
- 2 cases cover punctuation/whitespace variation and mixed Japanese/English wording.

The preserved V1 IDs are `address-registration-moving`, `national-health-insurance`, `national-pension`, `residence-tax`, `residence-status-renewal`, `student-to-worker-transition`, `part-time-work-permission`, and `employment-working-conditions`.

## Classification Method

The mock reference implementation applies NFKC Unicode normalization, English lowercasing, Japanese punctuation normalization, and whitespace normalization. It evaluates unique aliases, topic keywords, normal template terms, and strong template phrases. Repeated occurrences of the same evidence are counted once, and nested weaker terms do not add unlimited score.

Specific aliases and strong template phrases receive the largest weights. Ordinary keywords provide support, while broad words such as payment, insurance premium, deadline, permission, school, or notice cannot establish a trusted topic alone. Raw evidence is mapped consistently to a `0–1` confidence value. Trusted routing requires confidence of at least `0.68` plus specific evidence.

Close scores from two specific topics are rejected as ambiguous. Explicit uncertainty wording also blocks template override. A decisive exact template phrase may beat weaker generic evidence, but broad topic wording can return a topic without inventing a precise document template.

Deadline extraction requires both a supported, valid date and deadline/action context. Supported fixtures include Gregorian Japanese, slash, dash, dot, and valid Reiwa dates. Invalid dates and unrelated event dates return `null`.

## Metrics

Measured with `npm run test:evaluation` on 2026-10-15:

| Metric | Actual result |
| --- | ---: |
| Total cases | 54 |
| Classification correctness | 54 / 54 (100%) |
| Unknown/ambiguous rejection | 12 / 12 (100%) |
| False trusted matches | 0 |
| Deadline extraction correctness | 54 / 54 (100%) |
| Schema validity | 54 / 54 (100%) |
| Official warning presence | 54 / 54 (100%) |
| Related-guide correctness | 54 / 54 (100%) |

These are actual synthetic-suite results, not a claim of real-world accuracy.

## Confusion Cases

The suite currently has no failing cases. It explicitly passes Residence Tax vs National Pension, Residence Tax vs National Health Insurance, National Pension vs National Health Insurance, Residence-Status Renewal vs Student-to-Worker, Student-to-Worker vs Part-Time Work Permission, and Employment Contract vs general school/job information.

Remaining weak cases are outside the measured corpus: heavily damaged OCR, long documents that mention several procedures in different sections, unusual negation, and municipality-specific titles not represented in aliases may still fall back or require additional fixtures. Falling back is preferred to forcing a trusted result.

## Safety Checks

- No deadline is produced without an explicit valid deadline expression.
- No payment amount is extracted or invented by the mock trusted generator.
- Immigration results do not promise approval.
- Pension or tax exemptions are not described as automatically approved.
- Unknown, ambiguous, conflicting, and unrelated input can be rejected.
- Repeated keywords cannot inflate confidence.
- File-only mock uploads do not claim OCR occurred; recognized filenames remain clearly labeled as demo routing only.

## Limitations

- The classifier is deterministic and synthetic-fixture-driven, not a trained model.
- OCR is not implemented.
- A real AI fallback provider is not connected.
- Real Japanese documents vary by issuer, municipality, layout, wording, and OCR quality.
- The 100% result applies only to this 54-case dataset.

## Next Backend Step

The backend teammate can reproduce the normalization, unique-evidence scoring, ambiguity rejection, `0.68` trusted threshold, topic/template distinction, and deadline validation. The backend should keep classification metadata internal, route trusted content by stable IDs, validate the unchanged `DocumentAnalysisResult`, and use a cautious AI fallback only after the trusted classifier rejects the input.
