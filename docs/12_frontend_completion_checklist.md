# Frontend Completion Checklist

## Completed Without Backend

| Area | Status |
| --- | --- |
| Frontend pages | Complete: all planned routes exist |
| Responsive design | Complete: mobile and desktop layouts supported |
| Mock API layer | Complete: `src/api/client.ts` centralizes mock and future backend calls |
| Frontend UI states | Complete: loading, empty, error, validation, retry, no-deadline, and unknown-document states are represented |
| AI behavior design | Complete: prompt rules, schema, safety rules, and fallback behavior documented |
| Trusted knowledge structure | Complete: trusted topics and document templates exist as frontend-owned preparation assets |
| AI test cases | Complete: synthetic cases cover known, unknown, ambiguous, deadline, no-deadline, mixed-language, and conflict cases |
| Automated frontend tests | Complete: Vitest and React Testing Library cover core routes and flows |
| Accessibility pass | Complete: labels, focus visibility, async status/error messaging, and semantic structure reviewed |
| README | Complete: portfolio-ready project overview and setup instructions added |
| Deployment readiness | Complete: Vercel SPA rewrite config and environment variable docs added |
| Backend handoff | Complete: API contract, decoder flow, trusted-first strategy, and failure behavior documented |

## Waiting For Backend

| Area | Backend dependency |
| --- | --- |
| Real document analysis | `POST /api/documents/analyze` implementation |
| Real Life Guides API | `GET /api/guides` and `GET /api/guides/:id` |
| Real Official Resources API | `GET /api/resources` |
| Real Checklist API | `GET`, `POST`, `PATCH`, and `DELETE /api/checklist` |
| Authentication | Backend-owned if added |
| Real AI connection | Backend-owned OpenAI/provider integration |
| OCR and file handling | Backend-owned document processing pipeline |
| Full end-to-end integration | Requires deployed backend and real API responses |

## Final Frontend Gates

| Gate | Expected result |
| --- | --- |
| Install | `npm install` succeeds |
| Tests | `npm run test` succeeds |
| Build | `npm run build` succeeds |
| Routes | All eight routes load in mock mode |
| Mobile | Approximate `390x844` layout has no horizontal overflow |
| Excluded features | No Easy Japanese or Vocabulary feature exists in `src` |
| Backend independence | Mock mode works without backend |

## Return Point

Frontend work can pause after these gates pass. The next major phase should start when the backend teammate is ready to connect real APIs.

## Accessibility Notes

| Area | Current state |
| --- | --- |
| Semantic structure | Pages use semantic headings, `main`, navigation, forms, lists, and links |
| Forms | Document Decoder inputs have explicit labels and validation messaging |
| Async feedback | Decoder loading and errors use visible text and live regions |
| Keyboard focus | Global focus-visible styling is enabled for links, buttons, and form controls |
| Known limitation | No automated axe audit has been added yet; browser and Testing Library checks cover the main accessible names and flow behavior |
