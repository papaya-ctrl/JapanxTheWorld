# JapanxTheWorld Frontend Overview

## 1. Product Snapshot

| Item | Decision |
| --- | --- |
| Project | JapanxTheWorld |
| Primary users | Foreign students, job seekers, and workers living in Japan |
| Frontend owner | You |
| Backend owner | Your friend |
| Frontend stack | Vite, React, TypeScript, Tailwind CSS, React Router, `fetch` |
| Development mode | Mock data first, backend integration second |
| Supported devices | Mobile-first, tablet, desktop |
| UI language | Simple English first, designed to allow bilingual labels/content later |

## 2. Purpose

JapanxTheWorld helps users who struggle with Japanese documents, official procedures, and daily life tasks by giving them a clean interface, guided steps, and clear next actions.

## 3. Main Features

| Feature | Frontend goal | AI involvement |
| --- | --- |
| Document Decoder | Collect document input and display structured explanation results | High |
| Life Procedure Guides | Show practical step-by-step guides for common tasks | Low |
| Student-to-Worker Guide | Explain the transition path from study to work in Japan | Low |
| Official Support Links | Show trusted help resources and official websites | None |
| Dashboard / Checklist | Help users track progress and next tasks | None |

## 4. User Personas

| Persona | Situation | Frontend implication |
| --- | --- | --- |
| International student | Needs help understanding school, city hall, or immigration documents | Keep forms simple, show deadlines clearly |
| New worker | Needs support for residence, tax, insurance, and moving tasks | Use step-by-step cards and checklists |
| Job-seeking student | Wants to understand the path from student status to work status | Provide a dedicated transition guide page |
| Low-confidence Japanese reader | Can identify some document terms but not the full meaning | Use plain English and visual priority cues |

## 5. Frontend Responsibilities

| In scope | Out of scope |
| --- | --- |
| UI design and page layout | Authentication logic |
| Component architecture | Database design |
| Mock data and frontend state | OCR pipeline internals |
| AI response presentation rules | File storage infrastructure |
| API request integration layer | API business logic |
| Accessibility and responsive behavior | Server-side validation logic |

## 6. Product Rules

| Rule | Requirement |
| --- | --- |
| No Easy Japanese feature | Must not appear in docs, UI, or roadmap |
| No vocabulary feature | Must not appear in docs, UI, or roadmap |
| Trusted confirmation | Important actions must point users to official sources |
| Safe AI behavior | Frontend must not present AI output as final legal, immigration, tax, medical, or financial advice |
| One result shape | Template-based and AI-based document analysis must share the same response format |

## 7. Design Principles

| Principle | Frontend implementation rule |
| --- | --- |
| Clarity first | One main purpose per screen, short sentences, obvious buttons |
| Trustworthy tone | Use official warning blocks and source labels where needed |
| Mobile-first | Layouts must work well on small screens before desktop enhancement |
| Low-stress navigation | Keep route structure shallow and predictable |
| Reusable UI | Shared cards, badges, lists, and state blocks across pages |

## 8. Recommended Technical Decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Routing | React Router | Simple multi-page SPA structure |
| Styling | Tailwind CSS | Fast UI building and consistent spacing |
| API calls | `fetch` wrapped in small client helpers | Small surface area and easy future replacement |
| State | Local component state first | Enough for mock-first phase |
| Mock data | `src/data/*` | Enables frontend progress before backend exists |
| Domain types | `src/types/index.ts` | One shared contract for pages, components, and API responses |

## 9. Mock-First Development Policy

| Phase | Data source | Frontend expectation |
| --- | --- | --- |
| Phase 1 | Hardcoded mock objects | Fast page and component development |
| Phase 2 | Small API client wrapper returning mock data | Simulate async loading states |
| Phase 3 | Real backend endpoints | Replace mock implementation without changing page contracts |

### Mock-first rules

1. Every page must render useful UI before real APIs exist.
2. Mock data must match the future backend contract exactly.
3. Loading, empty, and error states must be designed before backend integration.

## 10. High-Level Deliverables

| Deliverable | Description |
| --- | --- |
| Docs package | Implementation-ready frontend and AI spec |
| Static frontend | Vite React app using mock data |
| API-ready client layer | Frontend adapter prepared for real backend |
| Portfolio-ready UI | Clean, modern, responsive interface |

## 11. Initial Task Checklist

| Task | Status target |
| --- | --- |
| Define routes and page roles | Required before coding |
| Lock shared types | Required before mock data |
| Define document analysis UI contract | Required before decoder page |
| Define component props and states | Required before component build |
| Define API contract with backend owner | Required before integration phase |

## 12. Acceptance Criteria

| Area | Acceptance criteria |
| --- | --- |
| Scope control | Docs cover only frontend and AI behavior design |
| Consistency | Pages, components, types, and API fields use matching names |
| Practicality | Every section includes tables, examples, or task lists |
| Readiness | A developer can start the Vite frontend without inventing missing decisions |
