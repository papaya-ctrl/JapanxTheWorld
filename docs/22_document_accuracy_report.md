# Step 12: document accuracy and reliability report

Prepared 24 October 2026; bounded measurements were collected on 23 October 2026.
**The evaluation suite is usable locally. Real-world accuracy remains incomplete;
Linux deployment and public production remain NO-GO.**

See the [reproduction/annotation guide](21_accuracy_evaluation_workflow.md),
[annotation schema](../backend/evaluation/annotation.schema.json), and
[allowlisted measured aggregate](step12_accuracy_aggregate.json). No real document
image, Japanese personal evidence, source path, actual private date/amount, secret
or prediction body is included in this report or aggregate.

## Evidence and sample counts

| Evaluation mode | Real documents | Synthetic image fixtures | Controlled OCR fixtures | Native OCR executed this step? |
| --- | --- | --- | --- | --- |
| Frozen Step 9 OCR, current engine replay | 1 partial | 11 | 0 | No; saved OCR boxes/confidence/geometry replayed |
| New bounded image corpus, final run | 0 | 16 | 0 | Yes, serial local PaddleOCR |
| Before/after extraction challenge suite | 0 | 0 | 20 | No; independently authored OCR inputs |
| Attempted fresh original dense corpus | 1 pending | 11 pending | 0 | No; initial memory guard refused all 12 |

There is **one available real document toward the target of forty**, not forty
collected samples. Its independently supplied known facts remain partially
annotated. There are **zero completely annotated real documents and zero real full
transcriptions**. A new encrypted version 2 scaffold references that existing sample
without modifying it; it remains unreviewed until independent human annotation.
No additional legitimate real documents were available. Thirty-nine additional
authorized inputs and complete independent review of the entire corpus are needed
to reach the target. No third-party documents were collected.

Twenty-seven distinct synthetic image fixtures were considered across historical
and fresh modes; only sixteen were freshly processed here. The twenty controlled
OCR specifications are separate fixtures, not additional photographed documents.
Repeated validation runs of the same sixteen images do not increase unique sample
counts. Before/after challenges use the same twenty inputs.

| Category | Real available/replayed | Step 9 synthetic images replayed | New synthetic images processed |
| --- | ---: | ---: | ---: |
| National Health Insurance Tax | 1 partial | 2 | 3 |
| Residence Tax | 0 | 1 | 2 |
| National Pension | 0 | 1 | 1 |
| Utility Bills | 0 | 2 | 1 |
| School Notices | 0 | 2 | 1 |
| Employment Documents | 0 | 1 | 1 |
| Municipal Notices | 0 | 1 | 1 |
| Unknown Documents | 0 | 1 | 6 |

The real categories beyond insurance are completely uncovered. Synthetic variants
include vertical columns, table headers/values, mild blur, repeated slips, paid
statements, examples, unknown notices and unreadable values. They use a small set
of authored labels and values; this is a convenience corpus, not population accuracy
or an independent test set for every supported Japanese layout.

## Measured field accuracy

All ratios below retain their sample/field denominators. Only verified predictions
are positive facts. A wrong semantic role is a false positive plus a false negative.
False-positive document rate means documents with any false verified field divided
by completely annotated documents; it is not a true-negative classifier FPR.

| Metric | Fresh native synthetic images (16) | Frozen synthetic replay (11) | Real frozen replay (1 partial) |
| --- | --- | --- | --- |
| Deadline precision | 12/12 = 100% | 13/13 = 100% | Unscored |
| Deadline recall | 12/12 = 100% | 13/13 = 100% | Full recall unscored; known-field recovery 2/2 |
| Deadline exact set/document | 16/16 | 11/11 | Unscored |
| Amount precision | 12/12 = 100% | 10/10 = 100% | Unscored |
| Amount recall | **12/13 = 92.31%** | 10/10 = 100% | Full recall unscored; known-field recovery 1/1 |
| Amount exact set/document | **15/16** | 11/11 | Unscored |
| False verified deadlines / amounts | 0 / 0 | 0 / 0 | Cannot determine from partial truth |
| Deadline / amount false-positive document rate | 0/16 / 0/16 | 0/11 / 0/11 | Unscored |
| Deadline label + annotated evidence/page support | 12/12 | Labels 13/13; page/source checks unannotated | Known labels 2/2; page/source checks unannotated |
| Amount label + annotated evidence/page support | **12/13** | Labels 10/10; page/source checks unannotated | Known labels 1/1; page/source checks unannotated |
| Document type | 16/16 | 11/11 | Known assertion 1/1 |
| Primary deadline | 16/16 | 11/11 | Known assertion 1/1 |
| Primary amount/null | **15/16** | 11/11 | Known assertion 1/1 |
| Extraction status | **15/16** | Not annotated | Known assertion 1/1 |
| Explicit uncertainty checks | 5/5 | Not annotated | Not separately annotated |
| Japanese-era checks | 3/3 | Not separately annotated | Not separately annotated |
| Repeated-amount checks | **1/2** | Not separately annotated | Not separately annotated |

The fresh run also produced two unverified date candidates and four unverified
amount candidates; these remain visible, not discarded. Exact-set scores concern
verified facts; explicit uncertainty checks separately test safe abstention. Missing
fields/unknown type, multiple deadlines and null primaries are explicitly annotated
in the new corpus. Omitted optional truth is unscored rather than converted to null.

Real field values, type, primary selections, partial status and complete extracted
field arrays were unchanged by the engine improvements when replaying the saved
real OCR. This demonstrates regression stability on **one frozen OCR result**.
It does not demonstrate fresh real OCR quality, real precision, complete real recall
or real false-positive rates. Legacy archive pairing uses anonymous IDs and lacks
an original input-hash binding; new version 2 runs bind source bytes to annotations.

Full-transcription edit scores are 3/650 normalized characters for the fifteen
transcribed new image fixtures and 40/537 for eleven historical synthetic fixtures.
The new vertical fixture's full transcription is intentionally unscored; field
evidence/page checks still apply. The historical vertical case contributes reading
order effects, so edit error is not automatically called a character-recognition
root cause. The real transcription score is unavailable. These bounded convenience
samples and correlated variants do not support confidence claims about real users.

## Critical failures, diagnosis and targeted changes

The twenty controlled OCR cases cover split dates, vertical text, tables/columns,
confusable characters, multiple deadlines, expiration/payment separation, fees,
paid/unpaid roles, detachable repeats, low confidence and unreadable/missing values.
The inputs and independent expected facts were measured before editing the engine.

| Confirmed failure | Change and regression evidence |
| --- | --- |
| An explicitly marked example deadline became verified | A nearby illustrative qualifier now prevents verification and preserves the candidate/evidence; regression S201 |
| An example payment amount became verified | Same scoped qualifier rule for monetary facts; S202 |
| An example title established a document type | Illustrative title evidence no longer confirms a type; S203 |
| An example paid stamp suppressed a genuine primary amount | Illustrative completion text no longer establishes paid status; S204 |
| A literal date written with kanji era numerals was missed | Strict parsing of ordinary 1–99 kanji numerals in era year/month/day, retaining calendar and era-boundary validation; S205 |

The qualifier rule is local to a nearby text clause; it does not invalidate every
field on a page containing a separate example. Literal numeral parsing performs
no OCR digit repair, calendar guessing or missing-year inference. Original Japanese
text, coordinates and confidence remain unchanged. No real sample-specific date,
amount, issuer or template was added to runtime rules. Separate regressions cover
clause boundaries, invalid kanji/era literals and all controlled safety expectations.

| Controlled metric | Before | After |
| --- | --- | --- |
| Deadline precision / recall | 6/7 / 6/7 | 7/7 / 7/7 |
| Amount precision / recall | 11/12 / 11/12 | 11/11 / **11/12** |
| False verified deadline / amount | 1 / 1 | 0 / 0 |
| Deadline exact documents | 18/20 | 20/20 |
| Amount exact documents | 18/20 | **19/20** |
| Type accuracy | 19/20 | 20/20 |
| Primary deadline / amount accuracy | 18/20 / 18/20 | 20/20 / 20/20 |
| Era conversion | 2/3 | 3/3 |
| Explicit uncertainty safety | 6/8 | 8/8 |
| Extraction status | 16/20 | 20/20 |

The remaining controlled amount false negative is intentional low-confidence input:
the known source amount remains in the recall denominator, while withholding its
verification/primary amount passes the safety expectation. A green regression test
therefore does **not** imply perfect amount recall.

The fresh native miss is **S111, the mildly blurred synthetic insurance image**.
Inspection of the generated source and encrypted prediction showed that Paddle
recognized a different glyph in the amount label at high recognition confidence.
The numeric text was recovered, but the supported payment-label association was
not established. The two occurrences merged as an unassociated unverified amount;
the primary stayed null and status became partial. That causes one amount FN,
one failed repeated-payment-group check and one primary/status mismatch against
the clear generator specification. It is not evidence that the engine summed
repeats or that its deduplication implementation is broken.

This synthetic case received an explicit prediction/truth-hash-bound review:
one OCR-recognition wrong-character error, zero independently assigned extraction
or interpretation errors **within that one reviewed case**. Other cases are
unreviewed for error cause; their cause counts are not implicitly zero. Real
error-stage reviews remain unavailable. No automatic lookalike substitution was
added to make the blurred case pass. A clearer capture or independent source check
is required before treating that amount as a confirmed payment fact.

## Performance and safety

Actual runtime: Darwin arm64, Apple M4, 16 GiB RAM, Python 3.12.13, PaddlePaddle
3.2.0, PaddleOCR 3.7.0, PaddleX 3.7.2, Pillow 13.0.0. Medium/Medium, batch 1,
four CPU threads, detector 1600, static backend and MKLDNN disabled are unchanged.
The worker cap remains **5 GiB**. One active model worker is leased globally;
all native runs were serial, completed and closed their worker.

| Identical Step 11 small benchmark | Step 11 | Step 12 |
| --- | --- | --- |
| First complete request | 2.6233 s | 2.0587 s |
| Model initialization | 1.9457 s | 1.4123 s |
| Median warm request | 0.5599 s | 0.5505 s |
| Sampled peak child RSS | 876.72 MiB | 891.56 MiB |
| End RSS increase across three requests | +0.46 MiB | +1.04 MiB |
| Sampled CPU, cold / warm | 71.5% / 91.6%, 92.7% | 84.3% / 98.7%, 89.7% |
| Processing failures | 0/3 | 0/3 |

The observed roughly 1.7% RSS increase and warm timing variation do not indicate
an unacceptable regression on this small workload. These short, noncontemporaneous
runs are not a statistical equivalence, leak, sustained-throughput or dense-image
regression proof. CPU sampling is coarse (100%=one core); initialization/cache and
background host state vary. Do not interpret faster startup as a measured engine
speedup. No model configuration was changed.

The sixteen-image final native corpus had 0 processing failures, 0.9651 s median
request time, 2.6325 s maximum/p95, about 891.05 MiB sampled peak RSS, 1.4636 s
initialization, 0.9638 s warm median, and 94.86% median sampled CPU. Its varied
640×640 fixtures differ from the identical 480×480 benchmark above. Container
memory is not applicable on this Mac and stays null, not zero.

Available host memory remained around 4–4.6 GiB with roughly 3.9 GiB swapped.
The 5 GiB initial-headroom guard refused fresh dense evaluation of all twelve
original inputs; pending rows and expected known-field counts were retained with
null new measurements. The 3 GiB exception accepted only bounded synthetic PNGs;
real inputs cannot use it. The runner also observes cgroup headroom, a stricter
768 MiB floor, 512 MiB swap-growth cancellation and production timeout/page/pixel
limits. Memory/timeout/crash safeguards passed their automated tests.

The historical dense Mac baseline remains approximately 4.2–4.3 GiB RSS and
9.6–9.8 seconds warm. Saved counters on the specific frozen replay are historical,
not new timings. No fresh dense or real-document memory/latency regression result
is claimed. Docker is still unavailable and memory insufficient for Linux staging;
no container or VM was started. Linux CPU, memory, latency and deployment readiness
remain unverified.

## Privacy, presentation and validation

Real images and sensitive annotations/results remain outside version control.
New annotation templates and retained predictions are authenticated encrypted,
with separate owner-only keys; private directories are 0700 and files 0600.
Plaintext source images and the original legacy annotations retain their existing
storage and permissions; this step does not claim to encrypt those in place.
Publication strips facts, source paths, hashes, notes and raw evidence. CLI errors
are generic. No name, address, account/insurance number or barcode from the real
sample was put into application logs or source control. The ignored original
sample's size/mtime and the zero-byte development DB were unchanged.

The frontend design and in-memory result/session handling are unchanged. Tests
verify English explanations, separate payment/usage dates, verified amounts with
null primary amounts, original Japanese evidence/pages, partial/unverified warnings,
no unsupported payment methods and no document-authenticity claim. An additional
React regression exercises illustrative amounts. The new backend rules generate
no unsupported payment instructions or official confirmation.

| Validation | Actual result |
| --- | --- |
| Backend full suite | **182 passed** (32 new evaluation/extraction regressions) |
| Frontend full suite | **113 passed** |
| Staging/backup suite | **9 passed** |
| TypeScript / production frontend build | Passed |
| Django system check / migration drift | No issues / no changes |
| Python / JavaScript dependency audits | Zero known vulnerabilities reported by pip-audit 2.10.1 / npm audit |
| Targeted static scan of new evaluation/runtime field code | Bandit 1.9.4: zero findings; not a native-library/image audit |
| Deterministic challenges | 20 measured before/after; all final safety expectations passed; one low-confidence accuracy FN retained |
| Fresh bounded synthetic native OCR | 16/16 processing success; one amount accuracy FN retained |
| Archived OCR replay | All 12 replayed; real known assertions unchanged |
| Fresh dense corpus | 12 explicitly pending due to memory guard |
| Privacy, encrypted artifacts, tamper/hash, denominator and resource tests | Passed within the backend/staging suites |
| Linux / public deployment | Not executed |

Initial annotation-test fixtures were corrected to provide the explicit category
required for reviewed data. Final automated checks passed. No passing result is
claimed for unavailable dense/Linux execution. The Step 11 37 HTTPS workflow checks
remain historical and are not counted as a fresh Step 12 run.

## Readiness and required human verification

| Area | Assessment |
| --- | --- |
| Automated regression/evaluation tooling | Usable for private local evaluation within resource limits |
| Real-world extraction accuracy | **Incomplete**: 1 partial real sample, no complete-real false-positive denominator |
| Linux deployment readiness | **NO-GO** pending actual suitable-resource execution and representative measurements |
| Public production | **NO-GO** pending real-corpus validation and Step 11 operational/TLS/recovery/privacy gates |

Humans must verify low-confidence or unreadable fields, conditional/examples,
conflicting/multiple primary candidates, paid versus unpaid/fee roles, unsupported
labels, blurry glyphs, incomplete dates/era boundaries, complex tables/vertical
layouts and any partial result against the original issuing document. Even a
verified extraction is a rule-based association, not independent confirmation of
the OCR text, a legal obligation or document authenticity. The current sample is
far too small to remove those checks.

Work remains uncommitted at the Step 11 base `f81a312`; no commit, push, paid API,
local LLM, public deployment, server purchase or document collection was performed.
