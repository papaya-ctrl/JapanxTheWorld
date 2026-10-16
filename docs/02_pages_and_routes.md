# JapanxTheWorld Pages And Routes

## 1. Route Map

| Route | Page | Main purpose | Data source in v1 |
| --- | --- | --- | --- |
| `/` | Home | Introduce platform and feature entry points | Static + mock summary data |
| `/document-decoder` | Document Decoder | Collect text or file metadata for analysis | Mock submit handler |
| `/document-decoder/result` | Document Result | Show structured analysis result | Mock analysis result |
| `/life-guides` | Life Guides | List daily life and official procedure guides | Mock guides list |
| `/life-guides/:guideId` | Guide Detail | Show one guide with steps and support links | Mock guide detail |
| `/student-to-worker` | Student-to-Worker | Explain transition path from study to work | Mock structured content |
| `/dashboard` | Dashboard / Checklist | Track tasks and completion state | Mock list + local persistence |
| `/help-center` | Help Center | Show official resources and support contacts | Mock resources |

## 2. Global Layout Rules

| Area | Requirement |
| --- | --- |
| Header | Persistent `Navbar` with logo, primary routes, mobile menu |
| Footer | Persistent `Footer` with support note and official-source reminder |
| Content width | Max width container with generous padding |
| Feedback states | Every data-driven page must support loading, empty, and error UI |
| Navigation | Current route should be visually highlighted |

## 3. Page Specifications

### `/` Home

| Item | Spec |
| --- | --- |
| Goal | Help new users understand what JapanxTheWorld does and where to start |
| Primary actions | Start Document Decoder, browse Life Guides, open Dashboard |
| Required sections | Hero, feature cards, trust message, quick links |
| Required components | `Navbar`, `FeatureCard`, `Footer` |
| Mock data | Feature descriptions and support highlights |
| Loading state | Not required in static v1 |
| Empty state | Not applicable |
| Error state | Not applicable |
| Future backend hook | Optional personalized dashboard shortcut after auth |

### `/document-decoder` Document Decoder

| Item | Spec |
| --- | --- |
| Goal | Let the user submit document text or upload a file placeholder for explanation |
| Primary actions | Paste text, select document category if known, submit analysis |
| Required sections | Intro note, privacy warning, input form, submit CTA |
| Required components | `DocumentInputForm`, `Navbar`, `Footer` |
| Mock data | Optional preset sample documents |
| Loading state | Submit button disabled, spinner, helper text |
| Empty state | Default form state before submission |
| Error state | Inline validation and analysis failure message |
| Future backend hook | `POST /api/documents/analyze` |

### `/document-decoder/result` Document Result

| Item | Spec |
| --- | --- |
| Goal | Display a single structured analysis result in a calm, readable layout |
| Primary actions | Review summary, read important points, follow next steps, open related guide |
| Required sections | Result header, urgency badge, summary, deadline, important points, next steps, warnings |
| Required components | `AnalysisResultCard`, `UrgencyBadge`, `ImportantPointsList`, `NextStepsList` |
| Mock data | `mockAnalysis.ts` |
| Loading state | Skeleton card after submit or refresh |
| Empty state | Fallback message if user reaches page without a result |
| Error state | Failed analysis or malformed result block |
| Future backend hook | Same output shape regardless of template or AI source |

### `/life-guides` Life Guides

| Item | Spec |
| --- | --- |
| Goal | Show available life procedure guides in a browsable list |
| Primary actions | Open a guide detail page |
| Required sections | Page intro, category filter placeholder, guide cards grid |
| Required components | `GuideCard`, `Navbar`, `Footer` |
| Mock data | `mockGuides.ts` summary list |
| Loading state | Card skeletons |
| Empty state | “No guides available yet” message |
| Error state | Retry banner with reload action |
| Future backend hook | `GET /api/guides` |

### `/life-guides/:guideId` Guide Detail

| Item | Spec |
| --- | --- |
| Goal | Present one procedure guide with steps and trusted references |
| Primary actions | Read steps, open official links, add a task to checklist later |
| Required sections | Guide header, who this is for, required documents, steps, official resources |
| Required components | `OfficialResourceCard`, `Navbar`, `Footer` |
| Mock data | `mockGuides.ts` detail objects |
| Loading state | Detail skeleton |
| Empty state | “Guide not found” block |
| Error state | Data fetch failure with retry |
| Future backend hook | `GET /api/guides/:id` |

### `/student-to-worker` Student-to-Worker

| Item | Spec |
| --- | --- |
| Goal | Explain the path from student status to work preparation in Japan |
| Primary actions | Review steps, open related life guides, save tasks mentally for dashboard |
| Required sections | Overview, timeline, required documents, common risks, related links |
| Required components | `FeatureCard` or dedicated content sections, `OfficialResourceCard` |
| Mock data | Static content object |
| Loading state | Not required in static v1 |
| Empty state | Not applicable |
| Error state | Not applicable unless later API-backed |
| Future backend hook | Optional CMS-backed content in later phase |

### `/dashboard` Dashboard / Checklist

| Item | Spec |
| --- | --- |
| Goal | Help users see progress and manage tasks in one place |
| Primary actions | View tasks, create task, toggle complete, edit, delete |
| Required sections | Progress summary, checklist form, task list, empty state help |
| Required components | `ChecklistItem`, `Navbar`, `Footer` |
| Mock data | `mockChecklist.ts` with local persistence behavior |
| Loading state | Short loading state if adapter becomes async |
| Empty state | Encourage adding first task |
| Error state | Save/update/delete feedback banner |
| Future backend hook | `GET/POST/PATCH/DELETE /api/checklist` |

### `/help-center` Help Center

| Item | Spec |
| --- | --- |
| Goal | Centralize official support links and practical help resources |
| Primary actions | Open official websites and support services |
| Required sections | Intro note, resource categories, official links cards, emergency advice note |
| Required components | `OfficialResourceCard`, `Navbar`, `Footer` |
| Mock data | `mockResources.ts` |
| Loading state | Resource skeleton cards |
| Empty state | “No resources available right now” block |
| Error state | Retry banner |
| Future backend hook | `GET /api/resources` |

## 4. Navigation Model

| Navigation item | Route | Priority |
| --- | --- | --- |
| Home | `/` | High |
| Document Decoder | `/document-decoder` | High |
| Life Guides | `/life-guides` | High |
| Student-to-Worker | `/student-to-worker` | Medium |
| Dashboard | `/dashboard` | High |
| Help Center | `/help-center` | Medium |

## 5. Route Data Dependencies

| Route | Required type(s) |
| --- | --- |
| `/document-decoder/result` | `DocumentAnalysisResult` |
| `/life-guides` | `GuideSummary[]` |
| `/life-guides/:guideId` | `GuideDetail` |
| `/help-center` | `OfficialResource[]` |
| `/dashboard` | `ChecklistItem[]` |

## 6. Page-Level Implementation Tasks

| Task | Applies to |
| --- | --- |
| Create route constants | All pages |
| Create base page containers | All pages |
| Connect mock data imports | Data-driven pages |
| Add loading and error placeholders | API-backed pages |
| Add links between related pages | Decoder result, guides, help center, dashboard |

## 7. Acceptance Checklist

| Check | Requirement |
| --- | --- |
| Route coverage | All eight routes exist |
| UI clarity | Each page has one obvious next action |
| Reusability | Shared components handle repeated UI patterns |
| Mock readiness | Every data-driven page works without backend |
| Integration readiness | Every API-backed page has a future endpoint mapping |
