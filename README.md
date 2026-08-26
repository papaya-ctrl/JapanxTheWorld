# JapanxTheWorld

JapanxTheWorld helps foreign students and workers in Japan understand difficult Japanese documents, official procedures, and practical next actions.

## Problem

Foreign students, workers, and students transitioning into work in Japan can struggle with official documents, city hall procedures, school notices, employment paperwork, and deadline-heavy tasks.

## Solution

JapanxTheWorld is a structured Japan-specific guidance platform. It uses **Trusted Knowledge First + AI Fallback**:

```txt
Known document or topic -> trusted JapanxTheWorld content
Unknown or low-confidence document -> AI fallback explanation
```

AI supports classification, fact extraction, and fallback explanations. Known procedures should rely on manually maintained trusted content instead of freeform AI generation.

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

The frontend is mock-first and backend-ready. Pages call `src/api/client.ts`, which can return local mock data or call backend endpoints depending on environment variables. The frontend-facing `DocumentAnalysisResult` shape stays the same for trusted template results and AI fallback results.

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
VITE_USE_MOCK_API=true
VITE_API_BASE_URL=http://localhost:8000/api
VITE_MOCK_API_SCENARIO=success
```

No secrets are required for the frontend prototype. Do not commit API keys, tokens, or private local environment files.

## Mock Scenarios

Use `VITE_MOCK_API_SCENARIO` or a document hint/text containing `simulate:<scenario>` for frontend QA.

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
- Backend integration pending
- Real AI API pending

## Screenshots

Screenshots are stored in `screenshots/`.

Expected files:

- `home-desktop.png`
- `document-decoder-desktop.png`
- `document-result-template-desktop.png`
- `document-result-ai-desktop.png`
- `life-guides-desktop.png`
- `guide-detail-desktop.png`
- `student-worker-desktop.png`
- `dashboard-desktop.png`
- `help-center-desktop.png`
- `home-mobile.png`

## Privacy / AI Disclaimer

JapanxTheWorld is a support tool. AI output and trusted guidance do not replace official confirmation. For immigration, tax, insurance, legal, medical, financial, government, school, or deadline-related decisions, users should confirm with the issuing organization or official sources.

## Roadmap

- Backend implements real `POST /api/documents/analyze`
- Backend implements real Life Guides, Official Resources, and Checklist APIs
- Backend adds authentication if needed
- Backend connects OCR/file handling and real AI provider logic
- Frontend switches `VITE_USE_MOCK_API=false` after APIs are ready
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

The mock-mode frontend is ready for static deployment.

For Vercel:

1. Set `VITE_USE_MOCK_API=true` for a standalone demo.
2. Set `VITE_API_BASE_URL` later when the backend is deployed.
3. Use the default build command: `npm run build`.
4. Use the output directory: `dist`.
