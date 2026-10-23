# JapanxTheWorld backend: Steps 7–10

`POST /api/documents/analyze` now uses local PP-OCRv6 Medium and the existing
Step 6 deterministic field engine. It does not call a template builder, classify
before field extraction, use an LLM, or require `OPENAI_API_KEY`. Existing health,
authentication, guide, resource, and checklist routes remain in place.

## Setup (Python 3.12)

The existing `backend/.venv` is supported. Dependencies are pinned to the tested
runtime; the OCR models are installed separately and are not downloaded by requests.
Django 5.2 LTS is retained; Step 10 updates DRF to 3.18.3 and Pillow to 13.0.0 with
patched transitive dependencies. See `requirements.txt` for the tested pins.

From the project root:

```sh
uv pip install --python backend/.venv/bin/python -r backend/requirements-dev.txt
backend/.venv/bin/python backend/manage.py check
backend/.venv/bin/python backend/manage.py test tests
backend/.venv/bin/python backend/manage.py runserver --noreload
```

Use `requirements.txt` instead of `requirements-dev.txt` when synthetic PDF test
fixtures are not needed. Existing database migrations are required for the other
application features, as before; uploads themselves make no database writes.

Cached model directories must exist under `~/.paddlex/official_models`:

- `PP-OCRv6_medium_det`
- `PP-OCRv6_medium_rec`

Set `DOCUMENT_OCR_MODEL_ROOT` to a different directory containing those two
folders if needed. Missing models return `503 OCR_UNAVAILABLE`; requests never
select or download substitute models. No API key is required. Model startup is
lazy and occurs only when an image or scanned PDF page needs OCR.

## Request and response

```sh
curl -X POST http://localhost:8000/api/documents/analyze \
  -F 'file=@/absolute/path/to/document.jpg'
```

Upload exactly one file in the `file` multipart field. Supported contents are
JPEG/JPG, PNG, WebP, and PDF. File signatures and decoder validity determine the
format; filenames never supply document facts. MIME declarations must agree with
the detected type or be `application/octet-stream`/empty. Pasted text and language
or document hints are ignored when a file is present. File-less/text-only requests
return `400 INVALID_REQUEST`; the legacy text/template/AI path is not exposed by
this endpoint anymore. Unsupported request media returns 415.

JPEG/MPO containers, including phone photos with additional frames, use the primary
frame and return an English warning and `pages[].auxiliaryFramesSkipped`. Other
animated or multi-frame image formats are rejected. EXIF orientation is not
silently applied: evidence coordinates describe the decoded primary image.

The response retains the full Step 6 `deadlines`, `amounts`, `primaryDeadline`,
`primaryAmount`, `evidence`, `warnings`, `extractionStatus`, `importantPoints`,
`nextSteps`, `summary`, `documentType`, and evidence-reference arrays. The engine
keeps conservative rules: unresolved monetary labels can keep `primaryAmount` null
while verified monetary fields remain in `amounts`. Duplicate detachable-slip
values are never summed. Usage/validity expiration dates cannot become the payment
or submission primary deadline. Unknown documents still support field extraction.

The upload schema adds these fields:

| Field | Contract |
| --- | --- |
| `source` | Always `"deterministic"` |
| `extractionMethod` | `"paddleocr"`, `"pdf_embedded_text"`, or `"mixed"` |
| `deadline` | Alias of `primaryDeadline`, including null |
| `urgency` | Null; no unsupported priority or legal urgency is inferred |
| `relatedGuide` | Null; no guide/template is substituted for document facts |
| `officialWarning` | Joined extraction warnings, or null |
| `pages` | One-based page, source method, coordinate system, width/height, skipped-frame count |
| `evidence[].extractionMethod` | Actual method for that source box |

Document type and summary may be null. Generated labels, descriptions, warnings,
reasons, and instructions are English; original Japanese is retained exactly in
`evidence[].text`. Every field references its source boxes. `verified` describes
extraction-rule checks, not independent authentication of the document or OCR text.

Text-only, unrotated PDF pages with usable Unicode character maps use PDFium's
embedded text and bounding boxes. Broken character maps, empty text, rotated
pages, and pages containing substantial raster images use a full-page render and
PaddleOCR. A mixed PDF can therefore use different methods per page. Pages are
processed serially, and raster buffers are released between pages. The embedded
text adapter uses a private score sentinel only to pass exact extracted text into
Step 6; the API restores `confidence: null` and `ocrConfidence: null` when no OCR
confidence exists. A mixed field's reported OCR confidence is the minimum actual
OCR score among its references; embedded text is not represented as 100% OCR.

Coordinate systems are declared per page:

- `image_pixels`: original decoded image, top-left origin.
- `rendered_pixels`: PDF rendered at 150 DPI, top-left origin.
- `pdf_points`: embedded PDF characters in points, converted to top-left origin.

Original box/character-group order is retained in `originalIndex`, separately from
reconstructed `readingOrder`. Paddle's detector input is bounded to a 1600-pixel
long side to control activation memory on large phone images. Paddle projects
its detections to source-image coordinates and recognizes crops at source
resolution. This uses the same Medium model weights, not an additional model.

Step 9 selects Medium detection/recognition, recognition batch one, four CPU
threads, `paddle_static`, and MKLDNN disabled. Configure these at server startup
through `DOCUMENT_OCR_CONFIGURATION`; uploads cannot override them. The image
adapter releases Pillow before inference and uses one packed BGR buffer; scanned
PDFs use a direct view of the PDFium BGR bitmap. Pages remain serial. No EXIF or
source-coordinate change is introduced. See the [measured comparison](../docs/15_ocr_optimization_benchmark.md)
for rejected Small/hybrid configurations and the limitations of detector resizing.

## Resource and abuse limits

Defaults are in `DOCUMENT_ANALYSIS_LIMITS` in `config/settings_base.py`:

| Limit | Default |
| --- | --- |
| File bytes | 10 MiB, checked during streaming and again before decoding |
| Request Content-Length | File limit plus 64 KiB multipart overhead |
| Non-file fields | 256 KiB total; at most 20 fields |
| Files | One |
| PDF pages | Five |
| Image/render dimensions | 8000 pixels on either axis |
| Image/render pixels per page | 16 million |
| Total rasterized PDF pixels | 50 million |
| Extracted boxes / characters | 4000 / 50,000 across the document |
| Worker processing time | 120 seconds, including cold model startup |
| Worker resident memory | 5 GiB, supervised via RSS |
| Minimum available host memory | 512 MiB; terminate worker on breach |
| Worker lifecycle | Exit after 120 seconds idle or 64 requests |
| Request rate | Six requests/minute per direct client address |
| Concurrent work per Django process | One; overlapping requests return 503 |
| Native workers sharing the lease path | One across application processes |

`DOCUMENT_ANALYSIS_RATE` can override the rate (for example `3/min`). Change limits
through Django settings and restart the server. Native file decoding, rendering,
and inference run in a spawned subprocess. Deadline or memory breaches terminate
the process; a subsequent request gets a fresh worker. RSS is sampled, so a native
allocation can briefly overshoot before termination. On Linux, deploy inside a
container/cgroup for an additional operating-system memory ceiling.

The model instance is reused safely across sequential requests, not initialized
per request. Text PDFs do not load it at all. Start with **one Django application
process** and bounded threads. A nonblocking lifetime file lease prevents duplicate
native workers across application processes using the same path. It defaults to
`~/.cache/japanxtheworld/ocr-worker.lock` and can be set with
`DOCUMENT_OCR_LOCK_PATH`. Its empty, owner-only inode is never unlinked. A cached
worker retains the lease between requests, so other application processes can
return 503 until it exits; this is not a broker. Containers with separate filesystems
and different hosts need explicit shared coordination. Idle/request-count recycling
releases model resources between jobs. The request lock prevents an unbounded
waiting queue; there is no automatic heavy retry or added layout model.

The default throttle uses Django's local cache and direct `REMOTE_ADDR`, ignoring
spoofable client-supplied forwarded addresses. Multiple application instances need
a shared cache and correctly configured trusted-proxy/client-IP handling. Configure
a reverse proxy request-body limit and upload/read timeout as well: the worker
time limit begins after the bounded upload has been received. Settings still
contain development `DEBUG`, hosts, secret-key, and cache defaults; deployment
hardening is separate from this integration and must precede public hosting.

Failures return English `code` and `message` without native exceptions or input:
400 invalid/empty/unsupported/malformed document, 413 input or memory limit, 415
request media, 422 unreadable/OCR failure, 503 busy/unavailable models, 504 timeout,
and 500 invalid internal result/unexpected failure. DRF throttling returns 429
with `detail` and `Retry-After`. Successful results and endpoint responses are
marked `Cache-Control: no-store`; 503 busy/unavailable responses include a short
`Retry-After`.

## Privacy and persistence

Uploads are bounded in memory and are **not** passed to Django's temporary-file
upload handler. PDFium and Pillow decode byte buffers; no document/debug files are
written by the pipeline. Native worker stdout/stderr are redirected to the null
device before loading parsers/models. Only a validated result, numeric metrics or
an allowlisted error code crosses the worker channel. Document names, text, account numbers,
exceptions, and results are not logged by application code.

The old persistence function stores filenames and generated summaries even when
raw-text storage is disabled. The upload route now bypasses that function entirely:
**no upload, filename, OCR evidence, summary, or analysis is stored in the database**,
regardless of `STORE_EXTRACTED_TEXT`. Existing rows and unrelated callers are not
modified. Returned JSON necessarily contains the source evidence; the client must
treat it as private and avoid analytics, console dumps, or persistent browser
storage by default. Native inference allocators may retain buffers for model reuse;
this is not a secure memory-erasure guarantee. No private test documents or debug
images are mapped to public Django routes.

## Tests and optional real-image check

```sh
backend/.venv/bin/python backend/manage.py test tests --verbosity 2
backend/.venv/bin/python backend/manage.py check
backend/.venv/bin/python backend/smoke_document_upload.py
```

The automated suite combines deterministic field tests with Django requests,
real synthetic image/PDF decoding, mocked OCR inference, and spawned worker tests.
It needs no model downloads or real private documents. Tests cover embedded and
scanned Japanese PDFs, formats, corruption/spoofing, limits, multiple dates,
deduplication, null primary fields, schema validation, no database writes,
English output, forbidden AI/template imports, worker/model reuse, cancellation,
and suppression of native stdout/stderr. Step 9 adds square-glyph vertical column
cases, evidence-backed literal notice titles, CPU settings, pixel preservation,
cross-process exclusion, recycling and private evaluation/report scoring. The final
suite has 108 backend tests; the existing 95 frontend tests and build also pass.

The optional smoke script defaults to the existing `backend/test_documents/sample.jpg`,
uses the actual endpoint and local models with no OpenAI key, makes two requests
to verify the same worker is reused (`--repeat 1` runs once), checks the input's
SHA-256 remains unchanged, and saves private JSON to
`~/ocr_private_test/step7-analysis.json` with owner-only permissions. It prints only
status/count/resource metrics, not OCR text or personal facts. Missing samples are
an error; this command is optional. Never commit the sample or private output.

## Step 8 frontend integration

The React Document Decoder now consumes this response contract in live mode.
See [the frontend integration notes](../docs/13_document_decoder_live_integration.md)
for upload setup, types/validation, partial results, source evidence, error handling,
and in-memory privacy behavior. The active upload form requires only a file;
manual hints and pasted text are not part of this flow.

The frontend keeps verified monetary entries visible when the primary amount is
null, distinguishes expiration dates from payment deadlines, and does not label
these deterministic results as AI-generated. No backend extraction rules or routes
were changed for Step 8. Broad real-document/PDF diversity, OCR worker memory under
load, resource sizing, and deployment controls still need validation before any
production-readiness claim.

## Step 9 evaluation and initial sizing

The [benchmark report](../docs/15_ocr_optimization_benchmark.md) and
[aggregate CSV](../docs/step9_benchmark_aggregate.csv) compare original settings,
Small/Medium combinations, CPU/detector settings, repeated endpoint requests and
eight PDF/size cases. The [evaluation guide](evaluation/README.md) explains private
ground truth and reproducible commands for up to fifty documents. Only eleven
synthetic images and one partially annotated real sample were available; full
real-document false-positive rates and OCR transcription accuracy remain unscored.

Final real endpoint requests measured 10.8 seconds cold / 9.6–9.8 seconds warm and
up to 4258 MiB worker RSS. The PDF/size suite peaked at 4408 MiB (4.30 GiB). Known
real fields and null primary amount/partial status were preserved. The old dense
real-image baseline stopped at host-pressure guards, so the historical 5.9 GiB
measurement is not a clean paired comparison. Broader documents can still exceed
the new limit and be safely rejected.

An 8 GiB RAM, four-vCPU CPU-only host with one heavy job is an initial estimate,
not a validated cloud minimum. The report includes current official base-price
examples, measured-throughput limits and deployment caveats. No cloud resources
were provisioned. Public deployment still requires Linux validation and the
existing settings/proxy/cache hardening.

## Step 10 production preparation

Development stays explicit in `config.settings_development` (with `config.settings`
as a compatibility alias). Public WSGI/ASGI startup defaults to
`config.settings_production`, which rejects missing secrets, hosts, origins and
private state paths. Production OCR requires an active Django account with
`models.analyze_document`; registration is closed, tokens expire after one hour,
and checklists are account-scoped. Local anonymous/demo behavior is confined to
development settings. Apply migrations only after a private backup; the existing
local database was not modified during this preparation.

Step 10 adds the missing authtoken app and additive migrations for the OCR permission
and the frontend's checklist category. Signature/decoder limits remain authoritative;
filenames must now also have an allowed JPEG/PNG/WebP/PDF suffix. The upload stream
stays in RAM and is explicitly closed on failures and cancellation. Production
body/IP/user limits fail closed, independently of the OCR worker lock.

The completed checks are recorded in the [readiness report](../docs/17_production_readiness_report.md):
133 backend tests, 112 frontend tests/build, dependency/security checks, disposable
migrations/backup/restore, a bounded native HTTP smoke and local Nginx proxy checks.
The [production guide](../docs/16_production_preparation.md) contains the environment,
Gunicorn/systemd/Nginx examples, low-cost sizing, migration and recovery procedures.
The [privacy draft](../docs/18_privacy_retention_draft.md) identifies retention and
hosting decisions still required. Public deployment remains NO-GO until operational
and accuracy gates are completed. No deployment, server purchase, commit or push
was performed.
