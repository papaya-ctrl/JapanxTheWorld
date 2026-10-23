# Step 8: live Document Decoder

The Document Decoder uploads one Japanese image or PDF to the Step 7 backend,
then displays its deterministic, evidence-based response in the existing result
layout. No document category, type hint, language hint, keywords, or pasted text
are required by the upload form. The frontend performs no AI calls or local LLM
inference. It does not infer facts from the filename.

## Run locally

From the project root, use Python 3.12 and the existing backend virtual environment
and cached PP-OCRv6 Medium models as described in [backend setup](../backend/README.md).

```sh
backend/.venv/bin/python backend/manage.py runserver 127.0.0.1:8000 --noreload
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://localhost:5173/document-decoder`. Configure `.env` using `.env.example`:

```env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=http://localhost:8000/api
VITE_MOCK_API_SCENARIO=success
```

Restart Vite after environment changes. Django must allow the browser's exact
origin in `CORS_ALLOWED_ORIGINS` (the existing default is `http://localhost:5173`).
Use the corresponding server/host configuration for a different origin. The
frontend sends the selected file as `FormData` under `file`; the browser supplies
the multipart boundary. Document uploads do not need database migrations, while
existing authentication/checklist features still require their backend database
setup. No unrelated backend routes or authentication behavior were changed here.

Live mode is the default, including when `VITE_USE_MOCK_API` is absent. Only the
literal value `true` enables explicit demo mode. Demo mode is visibly labeled and
retains legacy mock scenarios for tests/demos; it never reads the document's real
contents. Live mode does not call the mock analyzer or fall back to it after any
server, validation, timeout, or network failure. Vitest explicitly opts existing
mock tests into demo mode; dedicated live tests override it to false.

## Contract and display rules

`DocumentUploadResult` in `src/types/index.ts` mirrors the actual Step 7 Pydantic
schema. `src/api/documentContract.ts` validates nested fields, dates, source
references, statuses, page metadata, and verified primary selections without
coercing strings, supplying defaults, or accepting a legacy AI/template response
in live mode. The legacy result type remains a separate union variant for demos
and existing trusted-content tests.

- Unknown document type and absent summaries display neutral empty states.
- Date-only values use strict calendar validation and English month names without
  constructing timezone-dependent dates. Invalid dates are never repaired.
- `primaryDeadline` and `primaryAmount` are displayed exactly as selected by the
  analyzer. A null primary amount is never filled from another field.
- Verified entries from `amounts` remain visible even when `primaryAmount` is null.
  Unverified parsed candidates are marked as candidates; unreadable/null values
  remain unverified. There is no summing or selection by frontend array order.
- The backend's field labels and roles distinguish payment, submission,
  application, usage expiration, billed, already-paid, late-fee, and other fields.
  Repeated slip sections already merged by the backend appear once with their
  `occurrences` count. Different roles/statuses are retained even if values match.
- Overall statuses retain the exact API values: `verified`, `partial`, `unverified`,
  and `no_fields`. A verified field never turns a partial document into a complete
  extraction. Rule verification does not claim document authenticity.
- Evidence inspection uses only referenced boxes, with page numbers and original
  Japanese. Unrelated evidence, source IDs, coordinates, and raw OCR dumps are not
  displayed. Long blocks and long numeric identifiers are withheld with an
  instruction to inspect the original document instead. Evidence is collapsed by
  default. The browser still receives the private source data needed for the
  response contract; this is not a redaction service.
- No urgency, guide, payment method, procedure, or generic next action is invented.
  Important points, summary, warnings, and next steps come from the backend.

## Submission, loading, and errors

File selection supports JPEG/JPG, PNG, WebP, and PDF, with a 10 MiB client check
matching the backend's file limit. The picker and drag/drop flow also check empty
files and unsupported types. Missing browser MIME metadata may use the extension
only to admit a file for server validation; the backend validates actual contents.
No filename supplies document classification or facts. PDFs may contain up to
five pages under the current backend configuration.

While a request is pending, the form, retry, replace/remove, and upload controls
are disabled. A synchronous form guard and live-client single-flight guard prevent
rapid or cross-component duplicate requests. No automatic retries are performed.
Loading text accurately describes uploading and analyzing without pretending to
know a progress percentage or which server phase is currently active.

The client permits 150 seconds for upload, network, and backend processing (the
backend processing limit is 120 seconds). An abort or network interruption may
leave server work running; the timeout message says to wait before resubmitting.
Slow uploads may need a larger coordinated timeout in a future deployment. Leaving
the page does not submit a replacement job; a result arriving after unmount is
ignored. A new live submission while another client job is pending is rejected.

Backend error codes map to safe English messages for corrupted/unsupported files,
empty/oversized uploads, page/text/image limits, OCR unreadable/unavailable,
processing memory limits, timeout, busy server, and unexpected failure. HTTP 429's
actual DRF `detail` response is handled by status. The client honors `Retry-After`
for explicit manual retries and never displays an internal stack or arbitrary
server error payload. Errors remain errors rather than mock success results.

## Privacy

Uploaded files and extracted results are not written to localStorage,
sessionStorage, console logs, analytics, or external services by this flow. Preview
object URLs are revoked when a file changes, is removed, or the form unmounts.

Results are held in a React context owned by the app. Navigation history contains
only an opaque analysis ID; **the result object is not placed in browser history**,
which can otherwise survive a reload. Reloading or reopening the app clears the
in-memory result and shows a safe expired-result page. Opening a new decoder flow
clears the previous result. Late results after leaving the upload page do not
navigate or persist. App startup removes the legacy `japanxtheworld.lastAnalysis`
storage key and strips legacy raw result data from the current history entry;
older browser history entries from previous app versions cannot all be enumerated
or erased by this implementation. Checklist storage behavior is unchanged.

Private documents, OCR output, and screenshots from local evaluation must stay
outside source control. Do not put them in `public/`, static assets, fixtures,
analytics events, or logs. The default app still shows a local selected-file
preview; users should avoid screen sharing that preview when it contains private
information.

## Implementation files

- `src/types/index.ts`: separate deterministic and legacy demo response types.
- `src/api/client.ts`, `documentContract.ts`, `documentUpload.ts`: explicit live/demo
  switching, nested contract validation, file-only request, timeout and safe errors.
- `src/components/DocumentInputForm.tsx`: upload-only interaction, validation,
  loading, manual retry/cooldown, and preview cleanup.
- `src/context/AnalysisSession.tsx`, `src/App.tsx`: transient result lifetime.
- `src/pages/DocumentDecoder.tsx`, `DocumentResult.tsx`: submission/navigation,
  expiry recovery, and result-route scroll reset.
- `src/components/AnalysisResultCard.tsx`, `ExtractedDocumentFields.tsx`,
  `ResultStatusBlocks.tsx`: real fields, partial/verified states, and source snippets.
- `src/lib/documentDates.ts`: calendar-only English formatting.
- `.env.example`, `vite.config.ts`: live defaults and explicit test demo mode.

## Validation and remaining work

```sh
npm run test
npm run build
backend/.venv/bin/python backend/manage.py test tests
```

Tests cover actual file objects in image/PDF FormData, omitted hints, live mode
without fallback, malformed nested responses, primary/date validation, verified
amounts with null primary amount, status/evidence display, unknown/missing/unverified
fields, error codes, timeout and concurrency, Retry-After, preview cleanup, and
privacy-safe navigation/reload. Existing Home, Dashboard, Life Guides,
Student-to-Worker, resources, checklist and demo data tests remain in the suite.
Synthetic fixtures contain no real personal documents.

A browser smoke check can upload the existing private sample through the live UI.
Confirm exactly one request, English structured results, correct field roles,
partial status when applicable, and no guessed primary amount. Reload the result
to confirm expiry. Do not expose raw evidence during screenshots or save them in
this repository.

The historical Step 7 OCR worker measured roughly 5.9 GiB peak resident memory
against its former 6 GiB cap. [Step 9's measured evaluation](15_ocr_optimization_benchmark.md)
selects Medium/Medium, batch one, four CPU threads and detector side 1600, with
final real endpoint peaks around 4.2 GiB and a synthetic PDF/size-suite peak of
4.30 GiB. The worker limit is now 5 GiB, with host-memory guarding, a shared-path
process lease and idle/request recycling. The old dense-image baseline stopped
under current host-pressure guards, so these are not a clean paired percentage
improvement. Step 9 preserves the frontend design and response contract.

Memory remains a **backend production risk** beyond the measured corpus. One
partially annotated real document and synthetic fixtures do not establish broad
accuracy or sustained-load safety. Real-document/PDF diversity, Linux resource
sizing, proxy/upload timeouts, shared-rate limits and deployment hardening still
need validation. This integration does not claim production readiness.
