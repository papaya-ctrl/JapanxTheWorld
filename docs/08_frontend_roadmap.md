# JapanxTheWorld Frontend Roadmap

## Phase 1: Frontend Setup

| Item | Details |
| --- | --- |
| Goal | Create the Vite React TypeScript app and install Tailwind + React Router |
| Files to create | `package.json`, `vite.config.ts`, `tsconfig.json`, `src/main.tsx`, `src/App.tsx`, `src/index.css` |
| Components to build | None yet |
| Test checklist | App starts locally, routes compile, Tailwind styles load |
| Git commit message | `chore: initialize vite react frontend` |

## Phase 2: Static Pages With Mock Data

| Item | Details |
| --- | --- |
| Goal | Build page shells and shared layout using mock content |
| Files to create | `src/pages/*`, `src/components/Navbar.tsx`, `src/components/Footer.tsx`, `src/components/FeatureCard.tsx`, `src/data/*`, `src/types/index.ts` |
| Components to build | `Navbar`, `Footer`, `FeatureCard` |
| Test checklist | All routes render, navigation works, no backend dependency |
| Git commit message | `feat: add static pages and shared layout` |

## Phase 3: Document Decoder UI

| Item | Details |
| --- | --- |
| Goal | Build the decoder input page and submit flow using mock analysis requests |
| Files to create | `src/components/DocumentInputForm.tsx`, `src/pages/DocumentDecoder.tsx` |
| Components to build | `DocumentInputForm` |
| Test checklist | Form validation works, submit button loading state works, user can reach result page |
| Git commit message | `feat: add document decoder input flow` |

## Phase 4: AI Result Display UI

| Item | Details |
| --- | --- |
| Goal | Render the shared analysis result contract cleanly for template and AI outputs |
| Files to create | `src/components/AnalysisResultCard.tsx`, `src/components/UrgencyBadge.tsx`, `src/components/ImportantPointsList.tsx`, `src/components/NextStepsList.tsx`, `src/data/mockAnalysis.ts`, `src/pages/DocumentResult.tsx` |
| Components to build | `AnalysisResultCard`, `UrgencyBadge`, `ImportantPointsList`, `NextStepsList` |
| Test checklist | Result renders for both `source` values, `deadline: null` works, warning text shows |
| Git commit message | `feat: add document analysis result components` |

## Phase 5: Life Guides UI

| Item | Details |
| --- | --- |
| Goal | Create guide list and guide detail pages using mock guide data |
| Files to create | `src/components/GuideCard.tsx`, `src/pages/LifeGuides.tsx`, `src/pages/GuideDetail.tsx`, `src/data/mockGuides.ts` |
| Components to build | `GuideCard` |
| Test checklist | Guide cards render, route parameter opens detail page, not-found state works |
| Git commit message | `feat: add life guides pages` |

## Phase 6: Student-to-Worker UI

| Item | Details |
| --- | --- |
| Goal | Build the transition guide page with clear timeline and action content |
| Files to create | `src/pages/StudentWorker.tsx` |
| Components to build | Reuse `FeatureCard` or lightweight section blocks |
| Test checklist | Timeline and required steps are readable on mobile and desktop |
| Git commit message | `feat: add student to worker guide page` |

## Phase 7: Dashboard / Checklist UI

| Item | Details |
| --- | --- |
| Goal | Build the checklist dashboard with local mock persistence behavior |
| Files to create | `src/components/ChecklistItem.tsx`, `src/pages/Dashboard.tsx`, `src/data/mockChecklist.ts` |
| Components to build | `ChecklistItem` |
| Test checklist | Add, toggle, edit, and delete interactions work in mock mode |
| Git commit message | `feat: add dashboard checklist interactions` |

## Phase 8: Help Center / Official Links UI

| Item | Details |
| --- | --- |
| Goal | Build a help center page with official resources and support links |
| Files to create | `src/components/OfficialResourceCard.tsx`, `src/pages/HelpCenter.tsx`, `src/data/mockResources.ts` |
| Components to build | `OfficialResourceCard` |
| Test checklist | External links render clearly, empty and error states exist |
| Git commit message | `feat: add help center resources page` |

## Phase 9: Connect To Backend APIs

| Item | Details |
| --- | --- |
| Goal | Replace mock adapters with real backend calls without changing UI contracts |
| Files to create | `src/api/client.ts` |
| Components to build | None |
| Test checklist | All endpoints return mapped data, loading and error states behave correctly |
| Git commit message | `feat: connect frontend to backend api client` |

## Phase 10: UI Polish And GitHub Portfolio Preparation

| Item | Details |
| --- | --- |
| Goal | Improve trust signals, responsiveness, visual consistency, and README/demo quality |
| Files to create | `README.md`, optional assets/screenshots |
| Components to build | Final polish only |
| Test checklist | Mobile layout review, desktop layout review, build passes, screenshots ready |
| Git commit message | `style: polish frontend for portfolio presentation` |

## Cross-Phase Rules

| Rule | Requirement |
| --- | --- |
| No backend work | Do not implement server/database logic |
| No Easy Japanese feature | Keep out of roadmap and UI |
| No vocabulary feature | Keep out of roadmap and UI |
| Mock-first | Pages should always work before real API integration |
| Type safety | Add types before or with mock data, not after |

## Recommended Working Order This Week

| Priority | Focus |
| --- | --- |
| 1 | Phase 1 and Phase 2 |
| 2 | Phase 3 and Phase 4 |
| 3 | Phase 5 and Phase 7 |
| 4 | Phase 8, then Phase 9 |

## Definition Of Ready For Prompt 2

| Check | Requirement |
| --- | --- |
| Routes locked | Yes |
| Shared component list locked | Yes |
| Analysis result contract locked | Yes |
| API shapes locked | Yes |
| Folder structure locked | Yes |
| Build order clear | Yes |
