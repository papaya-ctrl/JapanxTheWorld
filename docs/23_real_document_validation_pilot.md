# Step 13: real-document validation pilot

Measured 27 October 2026. **One authorized issued document was available. Zero
documents meet the complete independent-human-review gate for the formal pilot.**
The bounded known-fact diagnostic completed, but expansion and formal pilot scoring
stop here until legitimate documents and independent annotations are supplied.
Public production remains **NO-GO**. No additional documents or results were invented.

This reuses the [Step 12 annotation/metrics workflow](21_accuracy_evaluation_workflow.md).
The [allowlisted measured aggregate](step13_pilot_aggregate.json) contains anonymous
IDs, counts and resource observations, without private source facts or paths.

## Available data and review status

| Dataset group | Actual unique samples | Fully human-reviewed pilot-eligible samples |
| --- | ---: | ---: |
| Actual issued documents | **1**, registered National Health Insurance Tax | **0** |
| Publicly available sample forms | **0** | **0** |
| Synthetic images used for stage investigation | **2**, existing S101/S111 clean/blurred controls | Excluded from real validation |

The issued sample is the existing user-authorized private image. Its Step 9 known
facts are partially annotated independently of predictions; Step 12's new review
scaffold is still unreviewed. No new human review, Japanese source transcription,
page-by-page evidence annotation or complete English interpretation was inferred.
The previously registered category is retained as metadata, not silently promoted
to a new completed review.

There are no real Residence Tax, Pension, utility, school, employment, municipal
or unknown-category samples available in this pilot. The target remains forty
diverse issued documents over time: thirty-nine additional authorized inputs and
complete independent review of this sample are needed. Public sample forms do
not fill this target, and synthetic fixtures never count as real-world validation.
No public forms or third-party personal documents were fetched or collected.

## Fresh issued-document diagnostic

Available host memory was approximately 5.5 GiB initially, above the existing
5 GiB initial-headroom requirement. One fresh native OCR request used the existing
partial known facts, followed separately by three serial performance requests on
the **same** document. That is one unique document, not four independent samples.
Only the first request was scored against known facts; the three timing requests
do not inflate accuracy denominators.

| Metric | Actual result and denominator |
| --- | --- |
| Unique issued samples processed/scored | 1/1 available |
| Complete real ground-truth samples | 0/1 |
| Known deadline recovery | **2/2** annotated fields |
| Known amount recovery | **1/1** annotated fields |
| Known exact value + semantic role matches | 2/2 dates; 1/1 amount |
| Known English label association | 2/2 dates; 1/1 amount |
| Full deadline precision / recall | **Unscored**, 0 completely annotated documents |
| Full amount precision / recall | **Unscored**, 0 completely annotated documents |
| Exact complete field-set accuracy | **Unscored** |
| False-verified critical deadline/amount counts and rates | **Not estimable** from partial ground truth |
| Known false negatives | 0 among the 2 dates and 1 amount; additional missing fields remain unknown |
| Unverified candidates retained | 0 dates, **7 amounts** |
| Duplicate verified entries | 0 observed; no independent repeated-group annotation, so deduplication accuracy is unscored |
| Independently annotated missing/ambiguous-field checks | 0 scored |
| Japanese source/page association checks | 0 independently annotated checks |
| Complete human-reviewed English interpretation | 0 scored |
| Category coverage | 1 insurance-tax document; all other real categories absent |

All known type, primary-field and partial-status assertions matched the existing
annotations. These are limited known-fact checks, not complete accuracy. Precision
and false positives are deliberately null rather than zero. Seven uncertain amount
candidates remain visible and do not become payment facts merely because some
digits were recognized. No unannotated field was declared correct or false.

The real result's generated fields/prose passed a local English-only check outside
source evidence. Japanese source text remains intact in the encrypted result.
This checks language presentation, not independent human confirmation of the full
interpretation. No private deadline, monetary value, name, identifier or issuing
details appear in this report or public aggregate.

## Blurred-image root-cause investigation

The investigation used the existing generated 640×640 clean control S101 and its
Gaussian-blurred counterpart S111, with the same selected Medium/Medium models.
One supervised child loaded one model and processed the two inputs serially.
All retained raw diagnostics are encrypted locally. The installed PaddleX 3.7.2
crop/recognizer calls were inspected and exercised directly, without sending an
image to a service or loading a second recognition model.

| Stage ablation | Clean S101 | Blurred S111 |
| --- | --- | --- |
| Amount lines detected | 2/2 | 2/2 |
| Minimum coverage of independently rendered line ink bounds | 99.46% | **100%** |
| Correct amount label in full-image OCR | 2/2 | **0/2** |
| Correct label, recognizer on detected crops | 2/2 | **0/2** |
| Correct label, recognizer on source-known oracle crops | 2/2 | **0/2** |
| Full-image recognition confidence | about 0.9970 | about **0.9575** despite the wrong glyph |
| Verified payment-amount groups in normal extraction | 1 | **0** |
| Verified group after diagnostic-only correction of the known label glyph | 1 | 1 |

The observed substituted label character is U+989D instead of the source's U+984D.
Both source-known oracle crops still produced the substitution. The digits were
recognized, but a supported payment label was not. This localizes the demonstrated
miss to **blur-associated text recognition**, rather than missing text detection,
reading-order loss or a broken canonical field-association rule. The clean/blurred
pair supports image quality as the trigger in these controls; it does not prove
that every blur or every occurrence of this glyph has the same behavior.

The diagnostic counterfactual changes only that generated label in memory, leaving
the recognized digits, confidence and geometry unchanged. Existing extraction then
associates the canonical label and merges the repeated sections. This establishes
that downstream layout/association can handle the controlled input when recognition
is correct. **No counterfactual result is returned by the application.** No automatic
lookalike replacement, guessed amount, alternate model or verification relaxation
was enabled.

After that diagnosis, two focused regressions were added: the observed high-confidence
wrong-label input must remain an unverified unknown-role amount with a null primary,
exact Japanese evidence and two occurrences; the canonical-label control must retain
the existing verified association/deduplication. The failure remains unresolved at
the recognition level. A clearer capture or independent source review is required;
an extraction-rule change is not justified by this evidence.

## Targeted evaluation changes

The existing version 2 contract and metrics are reused with backward-compatible
evaluation-only extensions:

- Issued documents retain `real_private`/`anonymized_real` provenance and `R###` IDs.
  Public forms now use `public_sample_form` and `P###`; synthetic fixtures use
  `synthetic` and `S###`. Reports separate all groups, and public-form coverage
  cannot fill missing issued-document categories.
- Optional `englishInterpretation` and `pilotReview` capture independently authored
  English meaning and an anonymous human checklist. The formal
  `--require-pilot-review` gate requires complete human truth, explicit null/missing/
  ambiguous-field decisions, review of dates/meanings, labels, paid/unpaid roles,
  multiple fields, Japanese evidence and English interpretation, and matching reviewer IDs.
- The registered sample's formal run was actually refused **before model creation**;
  no formal accuracy result was produced. The inventory records fixed review gaps.
  The ordinary explicit legacy-known-fact path remains available for labeled diagnostics.
- Existing legacy validation can consume decrypted annotations in memory, avoiding
  a persistent plaintext duplicate. The new Step 13 partial-annotation copy is
  encrypted; only this task's temporary duplicate was removed after an authenticated
  round trip. Original annotations and the source image were untouched.

Provenance and review declarations are human assertions, not software certification
that a document was issued or an interpretation is true. A completed checklist does
not replace independent annotation. Prediction/truth-bound post-output review uses
the existing OCR/field-extraction/interpretation/unresolved error stages.

No production extraction rule, selected OCR model, API response contract, frontend
design or transient in-memory result handling changed in Step 13.

## Memory and latency observations

Actual environment: Darwin arm64, Apple M4, 16 GiB RAM, Python 3.12.13,
PaddlePaddle 3.2.0, PaddleOCR 3.7.0, PaddleX 3.7.2 and Pillow 13.0.0. Configuration
remains Medium/Medium, batch 1, four CPU threads, detector 1600, static backend,
MKLDNN disabled and a **5 GiB worker RSS cap**. Requests were serial; workers closed.

| Issued-document measurement | Observed |
| --- | --- |
| Fresh scored diagnostic, cold | **13.0034 s**, 2.7438 s initialization, **4339.5 MiB** sampled peak RSS |
| Separate three-request benchmark, cold | **10.7251 s**, 1.0476 s initialization |
| Same worker, warm requests | **9.4778 / 9.5180 s**; median **9.4979 s** |
| Three-request benchmark maximum RSS | **3758.53 MiB** |
| End RSS growth, request 1→3 | **+140.8 MiB**; request 2→3 about +1.67 MiB |
| Sampled CPU, cold / warm benchmark | 103.3% / 103.9%, 104.7% (100%=one core) |
| Processing failures | 0/1 scored diagnostic; 0/3 performance requests |

The highest measured issued-document process RSS across these runs was about
**4.24 GiB**, consistent with the earlier approximate 4.2–4.3 GiB dense Mac range.
The separate benchmark's warm timing is close to the Step 9 9.6–9.8 s range. The
initial 13 s cold observation is also retained rather than hidden by the faster
benchmark. Cache/allocator state and background workload differ; these are bounded
observations, not a statistical equivalence or attribution to code changes.
The three-request RSS growth is not a leak/soak proof. Keep the existing recycling
and cap; do not size a server from the lowest observed peak.

The two synthetic full-image probe passes took about 1.056/1.035 s excluding crop
ablations, with about 887.7 MiB peak child RSS. These are diagnostic timings, not
real-document capacity. No Linux container ran: Docker was unavailable, and the
host lacked the Step 11 Linux-staging memory budget. Container memory remains
unmeasured/null. Linux performance and deployment readiness are unchanged.

## Reproduction and human gate

From the checkout root, using a new private output directory each time:

```sh
export PYTHONPATH=backend
PY=backend/.venv/bin/python
PILOT="$HOME/ocr_private_test/step13-new"
umask 077
"$PY" -m evaluation.accuracy keygen --output "$PILOT/keys/evaluation.key"
"$PY" -m evaluation.accuracy init --authorized --output "$PILOT/annotations/unreviewed.fernet" --key-file "$PILOT/keys/evaluation.key" /private/authorized/issued-document.png
"$PY" -m evaluation.pilot --manifest "$PILOT/annotations/unreviewed.fernet" --annotation-key-file "$PILOT/keys/evaluation.key" --output "$PILOT/review-inventory.json"
```

Only if an authorized public form actually exists, initialize it **separately**
with `--provenance public_sample_form`. Do not download forms or collect third-party
documents merely to inflate this pilot. Use the Step 12 decrypt/edit/encrypt workflow
for independent human annotation; add the full `pilotReview` checklist and English
interpretation from the original source before looking at predictions. Inspect
the exported [schema](../backend/evaluation/annotation.schema.json) for exact fields.
The inventory checks review eligibility; an actual run also verifies source hashes.

Once real review exists, run the formal gate; it must refuse the current scaffold:

```sh
"$PY" -m evaluation.accuracy run --manifest "$PILOT/annotations/reviewed.fernet" --annotation-key-file "$PILOT/keys/evaluation.key" --key-file "$PILOT/keys/evaluation.key" --require-pilot-review --output "$PILOT/qualified-run"
```

The measured known-fact diagnostic used the existing explicitly acknowledged legacy
annotations. Its encrypted copy can be rerun with `--legacy-known-facts` and
`--annotation-key-file`; this is **not** a bypass for formal pilot readiness. Retain
partial truth and null full-accuracy metrics. For the synthetic stage ablation,
with the existing Step 12 Mac-rendered corpus and its matching Arial Unicode font:

```sh
"$PY" -m evaluation.blur_probe --manifest "$HOME/ocr_private_test/step12/bound-small-dataset/manifest.json" --key-file "$PILOT/keys/evaluation.key" --output "$PILOT/blur/stage-ablation.fernet"
```

The probe uses installed PaddleX 3.7.2 internals and the known generated image
geometry; it is a local version-specific diagnostic, not a new public endpoint.
It explicitly accepts only the selected bounded synthetic samples. The performance
run reused Step 11's `staging_tools.benchmark.run(..., synthetic=False, repeat=3)`
on authorized local bytes, with no source values persisted. Keep native runs serial
and do not weaken resource guards. The new [regression tests](../backend/tests/test_real_document_pilot.py)
contain synthetic data only and require no model download.

## Validation, privacy and readiness

Final validation: **191 backend tests**, **113 frontend tests**, **9 staging/backup
tests** passed; production frontend build passed; Django system check and migration
drift check passed. The formal incomplete-review refusal was expected and tested.
No unavailable full-real-accuracy or Linux test is presented as passing.

All real images, annotation copies and sensitive predictions remain local and
outside Git; new retained sensitive artifacts are encrypted with a separate 0600
key, private directories 0700. Numeric metrics/review inventories contain anonymous
IDs and fixed categories, not personal source evidence. The original ignored image
and zero-byte development DB retained their size and modification time; input
hashes were checked unchanged. No personal document was shown to an external
service, uploaded to a remote development tool, or placed in application logs.

| Area | Assessment |
| --- | --- |
| Automated checks | Passing; evidence about software regressions only |
| Limited known-fact diagnostic | Completed on 1 authorized issued document; 2/2 known dates and 1/1 known amount |
| Formal real-document accuracy pilot | **Not qualified: 0 complete human-reviewed samples**; stop expansion/scoring until data/review exist |
| Blurred miss | Recognition substitution identified; remains safely unverified; no guessed correction |
| Linux staging | **Unverified / NO-GO** |
| Public production | **NO-GO**: insufficient real coverage and outstanding Step 11 operational/TLS/recovery gates |

Review the original whenever labels/glyphs are unclear, fields are conditional,
several values compete, paid and unpaid roles coexist, or results are partial.
Rule-verified extraction is not official confirmation or document authentication.
No deployment, purchase, commit, push or paid inference occurred. Work is uncommitted
on the Step 12 base `0cbde64`.
