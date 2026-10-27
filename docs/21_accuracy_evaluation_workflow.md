# Step 12: independent document accuracy evaluation

Use Python 3.12 and the existing `backend/requirements-dev.txt`. This extends the
[Step 9 framework](../backend/evaluation/README.md); it does not replace its
historical measurements. [Actual Step 12 results](22_document_accuracy_report.md)
separate fresh native OCR, frozen OCR replay, and controlled OCR inputs.

## Corpus and independent annotation

The target is **40 legitimately obtained real Japanese documents**, across National
Health Insurance Tax, Residence Tax, National Pension, utilities, school, employment,
municipal and unknown notices. The suite runs with one to fifty inputs. Forty is
a collection target, not a claim of statistical representativeness. Include hard,
blurry, vertical, table, multiple-deadline and repeated-slip cases rather than
selecting only easy documents. Record variants without presenting them as independent
people/documents. Exact duplicate image bytes are rejected to prevent count inflation.

Keep new documents and all sensitive annotations outside Git, preferably on an
encrypted local volume. The existing ignored private sample is referenced in place
and remains unchanged. Obtain authorization for any additional third-party input;
the CLI does not collect documents. Synthetic images remain explicitly synthetic.

From the checkout root:

```sh
export PYTHONPATH=backend
PY=backend/.venv/bin/python
EVAL="$HOME/ocr_private_test/step12-new"
umask 077
mkdir -p -m 700 "$EVAL"
"$PY" -m evaluation.accuracy keygen --output "$EVAL/keys/evaluation.key"
"$PY" -m evaluation.accuracy init --authorized --output "$EVAL/annotations/unreviewed.fernet" --key-file "$EVAL/keys/evaluation.key" /private/authorized/document1.png /private/authorized/document2.pdf
"$PY" -m evaluation.accuracy decrypt --input "$EVAL/annotations/unreviewed.fernet" --output "$EVAL/editing/manifest.json" --key-file "$EVAL/keys/evaluation.key"
```

Replace input paths with actual authorized files. `--authorized` records the
operator's declaration, not a consent verification service. Omitting it permits an
unreviewed scaffold, but running those inputs is refused. Initialization copies no
images and invents no categories, dates, amounts or null assertions. It records
SHA-256 input bindings and starts every real annotation as unreviewed. Input bytes
must remain unchanged; a changed image requires independent re-review. Files are
0600 and new directories 0700; existing artifacts are never overwritten.

The machine-readable [version 2 JSON Schema](../backend/evaluation/annotation.schema.json)
is generated from `evaluation/schema.py`. A reviewer edits the private JSON using
the original image/PDF. JSON Schema describes structure; the CLI additionally
enforces cross-field review/provenance, consistency and input-hash invariants.
Complete the annotation **before inspecting predictions**. Use anonymous reviewer
IDs such as `H001`. Do not use OCR output as ground truth or alter truth to improve
a score. Keep the unreviewed and reviewed versions separately.

Each document records `id`, private `path`, `inputSha256`, provenance, category,
authorization and ground truth. Real IDs are `R001` etc.; synthetic IDs are `S101`
etc. Category names are `national_health_insurance`, `residence_tax`,
`national_pension`, `utility`, `school`, `employment`, `municipal`, `unknown`.
An unreviewed category is null; unknown is an explicit reviewed classification.

Ground-truth fields:

| Field | Annotation rule |
| --- | --- |
| `verification` | `status`: unreviewed/partial/verified; `method`: pending/independent_human/synthetic_specification; real reviewed data requires an anonymous `reviewerId` |
| `complete` | True only for explicitly verified annotation; enumerate both deadline and amount lists, including genuine empty lists |
| `documentType` | Evidence-supported English type; explicit null asserts unknown; omit an unreviewed optional field |
| `deadlines` | Exact ISO date, semantic `kind`, canonical English `label`, independent source `evidence` with Japanese text and one-based page |
| `amounts` | Integer JPY value, semantic `kind`, English label, independent original evidence and page; never add repeated slip amounts |
| `primaryDeadline`, `primaryAmount` | A genuinely selected eligible field, or explicit null; omit if not yet annotated. A valid zero is a value |
| `extractionStatus` | verified/partial/unverified/no_fields when independently specified; omitted means unscored |
| `missingFields` | Explicit absence assertions for deadlines/amounts/type/primary fields; cannot conflict with annotated zero or uncertain candidates |
| `uncertainFields` | Field/role, optional candidate value/date, page evidence, reason and `mustNotBePrimary`; source ambiguity is distinct from a missed readable value |
| `eraChecks` | Original era literal, expected exact ISO date or null for an invalid literal, role and page |
| `repeatedAmounts` | Same role/value and expected source occurrence count; distinct paid/fee/payment roles remain distinct |
| `transcription` | Optional independent source transcription; not automatically populated from predictions |

For example, a **synthetic** field annotation is:

```json
{
  "kind": "payment",
  "date": "2031-06-30",
  "label": "Payment deadline",
  "evidence": [{"text": "納期限 令和13年6月30日", "page": 1}]
}
```

Date kinds include payment/submission/application/acceptance/response/return and
usage/validity expiration. Amount kinds include payment/billed/total/outstanding,
late_fee/paid/tax/unknown. A fee or paid amount cannot establish the primary payment.
Provide source snippets containing both the label and value where possible.
Calendar/era invalidity is not repaired; unreadable source fields remain uncertain.
For a low-confidence OCR test with a readable known source value, retain that known
value in truth: withheld verification is an accuracy false negative even when it is
the correct safety response. Do not rewrite that truth as missing to hide the miss.

After independent review, set partial/verified status appropriately and encrypt a
new version:

```sh
"$PY" -m evaluation.accuracy encrypt --input "$EVAL/editing/manifest.json" --output "$EVAL/annotations/reviewed.fernet" --key-file "$EVAL/keys/evaluation.key"
```

Protect the editing copy as sensitive data; remove it deliberately once no longer
needed. No automatic deletion, external storage or backup account is configured.
Keep a protected recovery copy of the key separately from result directories.
Fernet authenticates encrypted artifacts; it is not whole-disk protection or a
claim that plaintext never exists in memory. The source images remain on their
existing storage; encrypt their volume separately when appropriate.

## Metrics and denominator policy

Only verified predictions count as positive facts. A fact match requires semantic
role and exact ISO date/integer amount. Same-role duplicates do not inflate true
positives; a separate deduplication check catches extra entries and wrong occurrence
counts. Unverified candidates are retained and readable expected values they miss
are false negatives. Wrong roles count as a false positive plus a false negative.

For **complete** field annotations: precision is TP/(TP+FP), recall TP/(TP+FN),
exact match is correct complete field sets/documents, and the reported false-positive
rate is **documents with any false verified field / completely annotated documents**.
There is no well-defined count of every possible non-deadline/non-amount, so this
is not a true-negative-based classifier FPR. Zero denominators stay null.

For partial annotations, publish known-field recall and counts only. Full precision,
recall, exact-set accuracy and false-positive rate stay unscored. Unknown extra fields
cannot be declared correct or false from incomplete truth. Label-association
denominators include every annotated label, including missed fields; they do not
condition only on recovered fields. Evidence/page support, type, primary/null,
missing fields, uncertainty/partial status, era conversion and repeated amounts
have separate correct/scored counters.

Attempted processing failures stay in complete accuracy denominators and retain
known false negatives. Inputs **not executed** because of a resource guard remain
explicit pending rows with pending known-field counts and null measured accuracy.
They are not reported as successful or silently dropped. A CLI exit of zero means
report collection completed; inspect every outcome and denominator to assess quality.

Full transcription edit error uses existing NFKC/whitespace normalization and
bounded exact edit distance. Reading-order differences contribute to that score;
it cannot automatically establish a recognition root cause. Missing transcription
is unscored. Sample counts, correlated variants and convenience-corpus limitations
accompany every summary. Repeated runs do not create additional independent samples.

## Native evaluation and safe reproduction

Install the existing official Medium models separately; requests never download
models. Run one native evaluation at a time, with the API/model benchmarks stopped.
The new runner uses Step 11's supervised `LocalDocumentWorker` and global model
lease, batch 1, four CPU threads, detector 1600, static CPU backend, no MKLDNN,
5 GiB worker RSS cap, 120-second timeout, cgroup-aware headroom and 64-request
recycling. Evaluation uses a stricter 768 MiB remaining-memory floor and stops the
run after memory pressure or more than 512 MiB observed swap growth. No models are
changed and no cap is raised. Default model root is the existing local cache;
`--model-root` or `DOCUMENT_OCR_MODEL_ROOT` can select its installed location.

```sh
"$PY" -m evaluation.accuracy run --manifest "$EVAL/annotations/reviewed.fernet" --annotation-key-file "$EVAL/keys/evaluation.key" --key-file "$EVAL/keys/evaluation.key" --model-root "$HOME/.paddlex/official_models" --output "$EVAL/native-real"
```

Normal inputs require at least 5 GiB available before the first model starts.
The bounded exception requires **synthetic PNGs no larger than 640×640**, 3 GiB
initial headroom, and explicitly refuses real inputs. Generate and run it with:

```sh
"$PY" -m evaluation.fixtures_small "$EVAL/small"
"$PY" -m evaluation.accuracy run --manifest "$EVAL/small/manifest.json" --small-synthetic --key-file "$EVAL/keys/evaluation.key" --output "$EVAL/native-small"
```

Pass `--font /absolute/path/to/Japanese-font.ttf` on other systems. Images are
marked SYNTHETIC TEST; annotations come from generator specifications. Normal
production file/page/pixel limits remain in force. Reports record actual platform,
packages, settings, timings, sampled CPU/RSS/cgroup counters, input/truth hashes,
and implementation fingerprints. Sampling is 50 ms, CPU 100% means one core, and
missing counters are null. The worker closes in `finally`; guards never start Docker.
Do not interpret a short small-image run as dense-document or sustained-load evidence.

Reuse archived Step 9 OCR without loading a model:

```sh
"$PY" -m evaluation.accuracy replay --manifest "$HOME/ocr_private_test/step9/dataset/manifest.json" --archive "$HOME/ocr_private_test/step9/optimized-validated" --legacy-known-facts --key-file "$EVAL/keys/evaluation.key" --output "$EVAL/replay"
```

`--legacy-known-facts` explicitly acknowledges the original independently supplied
known facts. It never promotes a partial annotation to complete. Replay reconstructs
the saved OCR boxes, confidence, geometry and pages and runs the current deterministic
engine; its OCR timing/RSS counters remain historical. The legacy archive pairs
samples by anonymous ID and lacks an original input-hash binding; do not describe
that as fresh authenticated end-to-end OCR. New version 2 runs bind input bytes.

For an identical Step 11 workload performance comparison, run serially:

```sh
"$PY" -m staging_tools.benchmark --small-synthetic --repeat 3 --output "$EVAL/performance-after.json"
```

Linux/Docker execution remains governed by [Step 11 preflight](19_linux_staging.md).
Do not start a VM when memory or Docker availability is insufficient.

## Error review and publication

Raw predictions are saved only when `--key-file` is supplied, as authenticated
encrypted `R001.result.fernet` etc.; otherwise only numeric private metrics are
written. Private reports and CLI errors never echo source text, paths, exception
traces or credentials. Application logging and transient React result storage
remain unchanged.

```sh
"$PY" -m evaluation.quality_review template --metrics "$EVAL/native-small/metrics.json" --predictions "$EVAL/native-small" --key-file "$EVAL/keys/evaluation.key" --output "$EVAL/reviews/template.json"
```

An independent reviewer inspects the authorized original, annotation and encrypted
prediction privately, then creates a separate review file. Use only allowlisted
stage/category objects, for example `{"stage":"ocr_recognition","category":"wrong_characters"}`.
Stages are `ocr_recognition`, `field_extraction`, `interpretation`, `unresolved`.
Mark an entry reviewed only after inspection and declare `reviewerKind` as
`independent_human` for real inputs. `controlled_synthetic_investigation` is permitted
only for synthetic data. No copied names, account values or free-text notes enter
reviews. Prediction and ground-truth hashes bind reviews to exact versions; edited
outputs or truth invalidate a review. Unreviewed cause counts remain null, not zero.
Use unresolved rather than guessing a cause from a field mismatch.

```sh
"$PY" -m evaluation.quality_review apply --metrics "$EVAL/native-small/metrics.json" --predictions "$EVAL/native-small" --key-file "$EVAL/keys/evaluation.key" --reviews "$EVAL/reviews/reviewed.json" --output "$EVAL/reviews/reviewed-metrics.json"
"$PY" -m evaluation.quality_report "$EVAL/reviews/reviewed-metrics.json" "$EVAL/replay/metrics.json" --output "$EVAL/public-aggregate.json"
```

Publication allowlists fixed modes/categories/outcomes, anonymous IDs and finite
numeric counters. It recomputes summaries and strips paths, source facts, hashes,
Japanese snippets, arbitrary notes and prediction bodies. Review an aggregate
before deliberately copying it into Git. Real/synthetic provenance and historical/
fresh execution stay separate. Never merge repeats or inflate real coverage with
synthetic fixtures.

```sh
"$PY" backend/manage.py test tests
"$PY" -m unittest staging.test_artifacts
npm test
npm run build
```

The engine regressions cover measured illustrative-text false positives and literal
kanji-era conversion. Controlled cases also investigate split/vertical/table layout,
similar characters, multiple deadlines, expiration, paid/late-fee roles, repeats,
low confidence, missing/unreadable values and partial results. A missed blurred OCR
label stays unverified; no digit repair, unsupported payment instructions or real
sample-specific extraction rule is introduced.

Reproduce the controlled twenty-case measurement without OCR model loading:

```sh
"$PY" -m evaluation.challenges --output "$EVAL/challenges-after.json"
```

The reported before measurement was collected against the unmodified Step 11
engine at `f81a312`, using the same controlled specifications before fixing the
rules. It remains a separate run in the published aggregate. Current regressions
reproduce the fixes and retain the known low-confidence false negative.
