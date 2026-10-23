# Step 9: local OCR accuracy, memory and cost evaluation

Measured on 22 October 2026. The selected default is **PP-OCRv6 Medium detection +
Medium recognition, batch 1, four CPU threads, Paddle static backend, MKLDNN
disabled, detector long side capped at 1600**. Recognition still uses crops from
the original image. The Step 8 response contract and frontend design are preserved.
No paid inference service, local LLM, GPU, upload hints, or filename classification
is used.

This is a provisional choice for the available documents, not a production-readiness
claim. There is **one real private document, partially annotated, and eleven
explicitly synthetic images**. The framework supports up to fifty documents per
run; thirty to fifty independently annotated real documents are still needed.

## Environment and measurement

| Item | Measured configuration |
| --- | --- |
| Host | Apple M4, arm64, 10 logical CPUs, 16 GiB RAM, macOS 27.0.1 |
| Runtime | Python 3.12.13; PaddlePaddle 3.2.0; PaddleOCR 3.7.0; PaddleX 3.7.2 |
| Other libraries | NumPy 2.3.5; Pillow 12.1.0; PDFium binding 5.14.0; psutil 7.2.2 |
| Actual predictors | TextDetRunnerPredictor / TextRecRunnerPredictor |
| Actual inference runners | PaddleStaticRunner for detection and recognition |
| Old defaults | Medium/Medium; recognition batch 6; 10 CPU threads; MKLDNN requested; detector side 1920 |
| Optional models | Official Small detection and recognition, downloaded once outside Git |

Each profile runs serially in a fresh spawned process, reusing its model for warm
requests. The same ordered twelve-input manifest is used for the model matrix and
detector/thread tuning. Child RSS is sampled by the parent every 50 ms. Cold time
includes process startup, model initialization and the first document; warm time
excludes model initialization but includes decoding, OCR and field extraction.
The runner also records inference time, initialization RSS/time, end-of-request
RSS, parent RSS, per-page time, swap growth, and minimum available host memory.
These are sampled RSS observations, not exact allocator high-water marks or total
machine memory. Native allocators and macOS memory pressure affect repeatability.

Tests stop at 120 seconds, 6 GiB benchmark-worker RSS, less than 768 MiB host
available memory, or more than 512 MiB swap growth. Host-pressure cancellation stops
the entire run. The 6 GiB benchmark allowance exists to replay the old baseline;
the deployed default was **reduced to 5 GiB**, with an additional 512 MiB host
availability guard. Inputs are hashed before and after; the original sample was
unchanged. Private annotations, predictions and detailed metrics remain outside
the repository with restricted permissions. Child native output is suppressed.

## Baseline and final comparison

The historical Step 7 smoke script sampled the OCR child with psutil during two
endpoint requests: approximately 5980/6048 MiB peak RSS, 18.4 seconds cold and
17.5 seconds warm. That is the source of the earlier “5.9 GiB” observation; it
is not model-weight size or browser/server memory.

Two fresh attempts to run the original defaults on the dense real sample stopped
at the **host-memory guard**, after about 6.1/6.4 seconds. Their sampled peaks were
3416/4789 MiB; the second attempt observed about 564 MiB swap growth. These are
incomplete runs, not successful latency measurements. A fresh, successful paired
real-document baseline is unavailable. The historical result cannot establish a
controlled percentage improvement.

The eleven synthetic images did complete with the original implementation:

| Same synthetic images | Original defaults | Final implementation |
| --- | ---: | ---: |
| Successful images | 11/11 | 11/11 |
| Peak worker RSS | 3607 MiB | 3409 MiB |
| Cold first image | 5.29 s | 6.11 s |
| Median warm request | 3.43 s | 3.26 s |
| Deadline role + exact date | 13/13 | 13/13 |
| Amount role + exact value | 10/10 | 10/10 |
| Exact deadline / amount sets | 11/11 each | 11/11 each |
| Verified false deadlines / amounts | 0 / 0 | 0 / 0 |
| Exact English field labels among matched fields | 23/23 | 23/23 |
| Primary deadline / amount, including expected nulls | 11/11 each | 11/11 each |
| Document type, including unknown | 4/11 | 11/11 |
| Character edits / normalized reference characters | 40/537 | 40/537 |

The small warm-time difference is a single-run observation; the final cold request
was slower. Do not describe this as a universal speedup. The 7.45% character error
rate includes reading-order differences, especially vertical text; it is not an
isolated recognizer character score. Normalization uses NFKC and removes whitespace.
On complete synthetic annotations, false verified fields were 0/13 deadline
predictions and 0/10 amount predictions (0% false discovery in each, 100% precision),
and 0/11 documents contained a verified false field. A classical true-negative
false-positive rate is not defined by this field-set annotation scheme.

Three final **actual endpoint** requests on the real sample all returned HTTP 200:

| Request | Total time | Model initialization | Inference | Peak RSS |
| --- | ---: | ---: | ---: | ---: |
| Cold | 10.8 s | 1.07 s | 9.66 s | 4214 MiB |
| Warm | 9.6 s | 0 | 9.57 s | 4258 MiB |
| Warm | 9.8 s | 0 | 9.75 s | 4251 MiB |

All known dates and the annotated payment amount were recovered with their correct
roles. The primary amount remained null, seven monetary candidates remained
unverified, and extraction status remained partial. The worker was reused. Sampled
end-of-request RSS was approximately 4119, 4196 and 1886 MiB: no monotonic growth
in these three requests, which is insufficient to rule out leaks. The final native
twelve-document evaluation also passed all annotated fields, with the real request
at 9.79 seconds / 3651 MiB. Different allocator histories explain why that result
must not replace the more conservative repeated endpoint and load peaks for sizing.

## Model and pipeline decisions

The model matrix below used batch 1, CPU threads 4, no MKLDNN, the static backend
and detector side 1920 for every combination. Real-sample requests were warm after
the synthetic images. Peaks below refer to each subset; primary-field accuracy is
scored separately from whether individual fields were recovered.

| Detection / recognition | Synthetic cold / median warm | Synthetic peak | Real time / peak | Accuracy finding |
| --- | --- | ---: | --- | --- |
| Medium / Medium | 4.92 / 3.22 s | 3485 MiB | 11.93 s / 4856 MiB | All annotated fields and primary fields correct |
| Small / Small | 2.33 / 0.79 s | 1484 MiB | 3.82 s / 2358 MiB | Synthetic amounts 9/10; real primary deadline unresolved |
| Small / Medium | 2.22 / 0.90 s | 1485 MiB | 7.14 s / 2358 MiB | Synthetic fields correct; real dates 1/2 and primary deadline unresolved |
| Medium / Small | 4.53 / 3.21 s | 3003 MiB | 8.53 s / 5157 MiB | Synthetic amounts 9/10; real primary deadline unresolved |

All combinations matched 13/13 synthetic deadlines; complete synthetic annotations
produced no verified false fields. Small recognition/detection produced 51/537
character edits versus 40/537 with Medium detection in this corpus. Small/Medium's
missed real payment date had confidence below the existing verification threshold;
the threshold was not lowered. Faster Small profiles were rejected for the default
because they regressed known facts or primary-field selection. Small and Medium
support Japanese; Tiny was excluded because it does not. See the
[official PP-OCRv6 language support documentation](https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/docs/version3.x/algorithm/PP-OCRv6/PP-OCRv6.en.md).

The Small checkpoints came from the official PaddlePaddle repositories:
[detection](https://huggingface.co/PaddlePaddle/PP-OCRv6_small_det/tree/106c97591b235f607453300d9fc8c1cad1b25488)
and [recognition](https://huggingface.co/PaddlePaddle/PP-OCRv6_small_rec/tree/bd619643acac4b9650c040234da8d944476ee3f1).
The download utility pins revisions and records local weight hashes. Request
processing never downloads models or substitutes missing models.

| Investigated change | Evidence and decision |
| --- | --- |
| Recognition batch 6 → 1 | Original dense-photo baseline aborted; batch 1 completed three requests at 4936 MiB peak, 13.44 s cold / 11.73 s median warm. Accepted as a bounded viable configuration; isolated savings versus a successful original baseline cannot be calculated. Batch 2 is available as a profile but was not measured. |
| CPU 10 → 4, explicit static backend / no MKLDNN | CPU4/1920 completed the full matrix at 4856 MiB peak; CPU2/1920 took 12.36 s on the real image versus CPU4's 11.93 s, with 4689 MiB peak. Four threads selected; this does not establish a portable MKLDNN/thread memory effect on other platforms. |
| Detector 1920 → 1600 | Same batch1/CPU4 settings: real request 11.93 → 9.98 s and 4856 → 4166 MiB in tuning; all known fields preserved. Accepted provisionally. Full source pixels remain available for recognition and returned coordinates. |
| Detector side 1792 | Real verified amount missed despite correct synthetic fields; rejected. OCR response to scale is not monotonic. |
| Image/PDF buffer ownership | Pillow image closed before inference; one packed BGR byte buffer and read-only NumPy view. PDFium BGR bitmap viewed directly during its lifetime; no PIL/RGB/array round trip. Pixel/coordinate tests pass. This removes redundant copies structurally; no isolated end-to-end RSS gain is attributed to it. |
| Model reuse / lazy loading | Preserved, with numeric initialization and inference timings. Embedded text skips model creation. A cached worker may still retain model memory after an embedded-text request. |
| Duplicate native processes | Added a nonblocking, lifetime POSIX file lease before model loading, plus the existing per-parent single-flight lock. Two processes sharing the lease path cannot load concurrent OCR workers. Tests use fake models to verify exclusion/reuse. |
| Worker lifetime | Exit after 120 s idle or 64 requests; restart between jobs, including back-to-back requests at the recycling boundary. Retiring workers release the lease. No persistent waiting queue; overlaps return 503 with Retry-After. |

Medium detection and recognition parameter files total only about 133 MiB; sampled
RSS after model initialization was roughly 0.84–1.0 GiB, while inference peaked at
several GiB. Image buffers, activations, runtime libraries, caches and allocator
retention all contribute. Weight size alone does not explain peak memory.

## Deterministic extraction changes

Dense, aligned columns of square glyph boxes can now reconstruct vertical labels
and dates even when there is no single tall OCR box. The rule requires a tight
column with multiple Japanese characters; numeric table columns alone are excluded.
Unit cases cover a split vertical deadline, numeric-table separation and a
low-confidence glyph that must remain unverified. Existing horizontal split-box,
era conversion, paid/billed/late-fee, repeated-slip, ambiguity, issue/receipt date,
and payment-versus-expiration tests remain in place.

Five literal notice titles now support English document identification: pension,
electricity, school, employment conditions, and municipal notices. Their positive
tests require actual title evidence; generic or negated mentions remain unknown.
This does not select an extraction template or infer obligations. Synthetic title
ground truth was authored from the rendered titles, including titles previously
unsupported by the analyzer; all saved predictions were rescored against that same
truth. This accounts for the type improvement from 4/11 to 11/11. The synthetic
vertical/blurred/rotated images already recovered their known fields at baseline;
no additional end-to-end field-recall gain is claimed for those variants.

Confidence thresholds, uncertainty behavior, duplicate-value handling and primary
amount selection remain conservative. No digit repair, forced primary amount or
generic payment procedure was introduced. Source Japanese remains in evidence;
generated user-facing text remains English.

## PDF, input limits and bounded load

| Synthetic case | Result | Measured processing |
| --- | --- | --- |
| One-page scanned PDF | Correct fields, one OCR pass | 5.10 s cold; 3.55 s inference |
| Three-page scanned PDF | Correct fields, serial pages, three OCR passes | 10.36 s; 3.45 s/page inference |
| Embedded Japanese text PDF | Correct fields, zero OCR calls | 0.0028 s warm; already-cached model RSS is not incremental PDF memory |
| 3300×4500 image (14.85 MP) | Correct fields | 4.15 s; 4353 MiB peak |
| Image 64 bytes below 10 MiB | Correct fields | 3.53 s; 4383 MiB peak |
| Corrupted PNG | INVALID_DOCUMENT | Rejected |
| Image over 10 MiB | DOCUMENT_LIMIT_EXCEEDED | Rejected |
| Six-page PDF | DOCUMENT_LIMIT_EXCEEDED | Rejected |

There were five successful documents and three expected rejections, **zero unexpected
failures**, 10/10 annotated deadline roles/dates and 5/5 amount roles/values.
The suite's overall retained-worker peak was 4408 MiB (4.30 GiB), including rejection
requests after larger inputs. No real private PDFs were available.

Two simultaneous local Django API uploads accepted one request (200) and rejected
one (503 ANALYSIS_BUSY), without automatic retries. A follow-up returned 200 with
correct facts, confirming request association and recovery. Only one heavy job ran.
This test temporarily raised the in-process throttle to isolate concurrency from
rate limiting; it did not change saved settings. Peak worker RSS was about 3477 MiB.

Worker unit tests trigger timeouts and memory cancellation with deliberately tiny
limits and controlled child processes, then verify recovery. They do not exhaust
physical RAM or simulate a real operating-system OOM killer. Sampling can miss short
allocation spikes; a Linux cgroup remains necessary as an additional deployment
ceiling. The host-pressure baseline cancellations demonstrate why testing stops
rather than repeatedly pushing the machine into swap.

## Deployment estimate and costs

An initial **8 GiB RAM / 4 vCPU CPU-only VM, one Django application process and one
OCR child, one active heavy job** is a practical estimate from the observed 4.30 GiB
worker peak, parent/server memory, operating system and safety headroom. A 4 GiB VM
is smaller than the measured worker alone. Eight GiB is not a measured cloud minimum;
Linux wheel availability, backend behavior, dense five-page documents and resident
memory must be verified on the chosen machine before opening access. Keep the 5 GiB
worker guard, use an OS memory ceiling with server headroom, bound web threads,
configure HTTPS/body limits and a proxy timeout above the 120 s processing limit.

On this Mac, dense single-page warm requests imply about **6 documents/minute** in
serial operation; the small synthetic scanned pages imply about 17 pages/minute.
These are reciprocals of observed processing times, not sustained-throughput tests.
The existing six-requests/minute/client throttle and 503 overload response still
apply. Shared VM CPUs may be slower and more variable. Do not sell these estimates
as a cloud SLA. Start with no background queue; a future queue must have explicit
capacity and privacy/lifecycle rules.

Monthly base-price examples checked after sizing, on 22 October 2026:

| Candidate | Resources | Published monthly base | Qualification |
| --- | --- | --- | --- |
| Hetzner CX33, Germany/Finland | 4 Intel/AMD vCPU, 8 GB RAM, 80 GB NVMe | €8.49, excluding VAT and IPv4 | Product page marked unavailable at lookup; this is a published schedule, not a guaranteed purchasable offer. |
| DigitalOcean Basic Regular | 4 vCPU, 8 GiB RAM, 160 GiB SSD | US$48 | Shared CPU; validate performance on Linux before choosing. |

Hetzner specifications and availability are from its
[cost-optimized product page](https://www.hetzner.com/cloud/cost-optimized/), and
the price is from its [June 2026 price schedule](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/).
DigitalOcean resources and price are from its
[official Droplet pricing](https://www.digitalocean.com/pricing/droplets).
Taxes, domains, optional backups, additional networking/storage and region-specific
charges are outside these base estimates. No cloud resources were purchased or
provisioned. Hosting the static frontend and reverse proxy on the same VM is a
low-cost initial option; inference requires no metered AI API.

The lifetime lease coordinates only processes sharing its filesystem path and
permissions. Independent containers/hosts need an explicit single-owner service
or shared coordination. With several Django parents, a cached child can own the
lease while other parents return busy; use one application process initially.

## Reproduction, verification and remaining gaps

See [evaluation commands and annotation schema](../backend/evaluation/README.md).
The [aggregate CSV](step9_benchmark_aggregate.csv) contains only numeric results,
fixed profile names and provenance. Runs are: 1 original synthetic; 2 original real
guarded retry; 3 batch1 real repeats; 4 model matrix; 5 detector/thread tuning;
6 first optimized adapter run; 7 final title-rule validation; 8 PDF/size suite.
The first host-guarded attempt and the three final endpoint smoke measurements
are described above separately. Blank real-document false-positive/CER values mean
unscored, not zero. Expected load rejections are distinguished from failures.

Final automated checks: **108 backend tests, 95 frontend tests, production frontend
build, Django system check and dependency check passed**. Tests do not download
models. No frontend source changes were needed for Step 9. Worker process exclusion,
reuse, idle/request recycling, timeout/memory cancellation and pixel coordinates
have regression coverage. The original private sample remained unchanged; no
personal images, raw OCR, private facts or predictions are published here.

The real document has known-field annotations, not an exhaustive transcription.
Its full false-positive rate and CER are unavailable. Synthetic false-positive
counts are zero across eleven complete images, which is not evidence of a low
population error rate. Label scores cover matched fields; recall must be read
alongside them. Long-duration allocator growth, other fonts/layouts, skew/blur,
vertical financial tables, real PDFs, multi-user sustained load, Linux/x86
deployment and 30–50 independently annotated real images remain unverified.
Development settings and shared-cache/proxy hardening also remain deployment work.
