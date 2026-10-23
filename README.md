# JapanxTheWorld

JapanxTheWorld helps foreign students and workers in Japan understand difficult Japanese documents, official procedures, and practical next actions.

The Document Decoder now uploads Japanese images/PDFs to the local Django/PaddleOCR
backend and displays evidence-based English results. See [live decoder setup,
privacy, tests and limitations](docs/13_document_decoder_live_integration.md) and
[backend setup](backend/README.md). Explicit mock/demo mode remains available for
other frontend QA and demonstrations.

## Problem

Foreign students, workers, and students transitioning into work in Japan can struggle with official documents, city hall procedures, school notices, employment paperwork, and deadline-heavy tasks.

## Solution

The live Document Decoder uses local PaddleOCR or embedded PDF text extraction
and deterministic Python rules to identify supported fields. It preserves source
evidence, separates verified and unverified values, and leaves unsupported primary
fields null. No paid AI API or local LLM is part of this upload workflow.

Life Guides use maintained trusted content. Legacy template/AI-style results
remain explicit demo fixtures rather than live document facts.

## Target Users

- Foreign students in Japan
- Foreign workers in Japan
- Students transitioning from school to work in Japan

## Main Features

- Document Decoder
- Life Guides
- Student-to-Worker guide
- Dashboard / Checklist
- Official Support links

## Tech Stack

| Area | Stack |
| --- | --- |
| Frontend | React, TypeScript, Vite |
| Styling | Tailwind CSS |
| Routing | React Router |
| Tests | Vitest, React Testing Library, jsdom |
| API layer | Centralized `fetch` adapter in `src/api/client.ts` |
| Deployment target | Static frontend deployment, prepared for Vercel |

## Frontend Architecture

Pages call `src/api/client.ts`. Live document uploads use the actual deterministic backend contract; explicit demo mode retains the legacy template/AI simulation contract. Other pages keep their existing API and demo behavior.

The Document Decoder accepts JPEG/PNG/WebP images or PDFs without manual hints. Live mode performs OCR or embedded PDF text extraction in the backend. Explicit demo mode is visibly labeled and does not read uploaded file contents.

## Project Structure

```txt
docs/
├── 01_frontend_overview.md
├── 02_pages_and_routes.md
├── 03_component_spec.md
├── 04_ai_document_decoder_spec.md
├── 05_api_contract_with_backend.md
├── 06_ui_state_and_error_handling.md
├── 07_frontend_folder_structure.md
├── 08_frontend_roadmap.md
├── 09_ai_evaluation_plan.md
├── 10_ai_backend_handoff.md
├── 11_trusted_knowledge_strategy.md
└── 12_frontend_completion_checklist.md
src/
├── api/
├── components/
├── data/
├── pages/
├── test/
├── types/
├── App.tsx
├── index.css
└── main.tsx
screenshots/
```

## Setup

```bash
npm install
npm run dev
```

Open the local URL printed by Vite.

## Environment Variables

```env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=http://localhost:8000/api
VITE_MOCK_API_SCENARIO=success
```

No secrets are required for the frontend prototype. Do not commit API keys, tokens, or private local environment files.

## Mock Scenarios

Set `VITE_USE_MOCK_API=true` explicitly to use demo mode. Use `VITE_MOCK_API_SCENARIO` for frontend QA; legacy text-based simulations remain test helpers and are not active upload-form inputs.

| Scenario | Behavior |
| --- | --- |
| `success` | Standard mock success |
| `trusted-template` | Trusted-style template success |
| `ai-fallback` | AI fallback result |
| `timeout` | Simulated timeout error |
| `server-error` | Simulated recoverable server error |
| `malformed` | Simulated malformed analysis error |
| `unknown-document` | Unknown document result |
| `no-deadline` | Result with `deadline: null` |
| `empty-guides` | Empty Life Guides list |
| `resources-error` | Failed Official Resources fetch |
| `checklist-mutation-error` | Checklist create/update/delete failure |

## Current Status

- Frontend implementation complete
- Mock mode complete
- Trusted knowledge structure complete
- AI behavior and backend handoff docs complete
- Live Document Decoder integration complete (Step 8)
- Local OCR comparison, bounded worker lifecycle and private accuracy evaluation implemented (Step 9)
- Production settings, authorized OCR, private checklist access and deployment preparation implemented (Step 10)
- No paid AI service required for document uploads
- Public deployment remains NO-GO pending operational setup and broader evaluation

See the [Step 9 benchmark report](docs/15_ocr_optimization_benchmark.md) for measured
memory/latency, rejected model choices, accuracy limits and initial hosting costs,
and the [backend evaluation guide](backend/evaluation/README.md) for reproduction.
Production setup and remaining gates are in the [preparation guide](docs/16_production_preparation.md),
[readiness report](docs/17_production_readiness_report.md) and
[privacy draft](docs/18_privacy_retention_draft.md).

Step 11 adds [disposable Linux staging commands](docs/19_linux_staging.md) and an
[updated staging readiness report](docs/20_staging_readiness_report.md). Bounded
macOS HTTPS/OCR/recovery checks passed; Linux container execution remains pending
because Docker was unavailable and host memory was insufficient. Public deployment
remains NO-GO.

## Privacy / AI Disclaimer

JapanxTheWorld is a support tool. Extracted results and trusted guidance do not replace official confirmation. For immigration, tax, insurance, legal, medical, financial, government, school, or deadline-related decisions, users should confirm with the issuing organization or official sources.

## Roadmap

- Live `POST /api/documents/analyze` integrated with the Document Decoder
- Backend implements real Life Guides, Official Resources, and Checklist APIs
- Validate authorized accounts, migrations and Linux/proxy operations before hosting
- Expand evaluation to 30–50 independently annotated real documents and validate Linux deployment
- Live mode is the default; use explicit mock mode only for demos/tests
- Full end-to-end QA after backend integration

## My Role

Frontend implementation and AI behavior design.

## Team Role Split

Backend, database, authentication, file handling, OCR/backend document processing, and real API implementation are handled by the backend teammate.

## Commands

```bash
npm run dev
npm run test
npm run build
npm run preview
```

## Deployment

No application was deployed by Step 10. For a future Vercel frontend, production
requires a separate HTTPS Python backend URL, `VITE_USE_MOCK_API=false`,
`VITE_REQUIRE_AUTH=true`, matching CSP/CORS origins, build `npm run build` and output
`dist`. Never put account tokens or backend secrets in `VITE_` variables. The build
fails if the Vercel backend/CSP configuration is incomplete. Use the
[production preparation guide](docs/16_production_preparation.md) rather than a
development server for public hosting. OCR remains on the Linux backend.
