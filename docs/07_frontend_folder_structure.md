# JapanxTheWorld Frontend Folder Structure

## 1. Target Structure

```txt
src/
├── api/
│   └── client.ts
├── components/
│   ├── Navbar.tsx
│   ├── Footer.tsx
│   ├── FeatureCard.tsx
│   ├── DocumentInputForm.tsx
│   ├── AnalysisResultCard.tsx
│   ├── UrgencyBadge.tsx
│   ├── ImportantPointsList.tsx
│   ├── NextStepsList.tsx
│   ├── GuideCard.tsx
│   ├── ChecklistItem.tsx
│   └── OfficialResourceCard.tsx
├── data/
│   ├── mockAnalysis.ts
│   ├── mockGuides.ts
│   ├── mockResources.ts
│   └── mockChecklist.ts
├── pages/
│   ├── Home.tsx
│   ├── DocumentDecoder.tsx
│   ├── DocumentResult.tsx
│   ├── LifeGuides.tsx
│   ├── GuideDetail.tsx
│   ├── StudentWorker.tsx
│   ├── Dashboard.tsx
│   └── HelpCenter.tsx
├── types/
│   └── index.ts
├── App.tsx
├── main.tsx
└── index.css
```

## 2. Folder Responsibilities

| Folder | Responsibility |
| --- | --- |
| `src/api` | Frontend request helpers and future backend integration layer |
| `src/components` | Reusable UI building blocks |
| `src/data` | Mock data matching backend contract fields |
| `src/pages` | Route-level page components |
| `src/types` | Shared TypeScript domain models |

## 3. File Responsibilities

| File | Responsibility |
| --- | --- |
| `src/api/client.ts` | Shared `fetch` wrapper plus mock-ready adapter functions |
| `src/types/index.ts` | Export all domain and API-facing types |
| `src/App.tsx` | Route definitions and app shell |
| `src/main.tsx` | Vite entry point |
| `src/index.css` | Tailwind imports and shared custom styles |

## 4. Data Flow Rule

```txt
mock data or API client -> page component -> presentational component
```

### Implementation rule

1. Pages own data loading and status handling.
2. Presentational components receive typed props and avoid direct fetching.
3. Mock data must use the same field names as the future backend.

## 5. Mock-To-Real API Swap Strategy

| Stage | `src/api/client.ts` behavior | Page impact |
| --- | --- | --- |
| Early build | Return promises from mock data | No page changes |
| API integration | Replace mock implementations with `fetch` calls | Minimal or no page changes |
| Error simulation | Throw mock `ApiError` objects during development | No component contract changes |

## 6. Optional Additions

| Folder | Add only if needed | Reason |
| --- | --- | --- |
| `src/hooks` | Yes | Shared UI/data hooks such as checklist persistence |
| `src/layouts` | Yes | If route-level layout wrappers become repetitive |
| `src/utils` | Yes | Date formatting, validation, route helpers |

## 7. Naming Conventions

| Area | Convention |
| --- | --- |
| Components | PascalCase file names |
| Pages | PascalCase file names matching page role |
| Types | Singular/plural names that match API payload meaning |
| Mock files | `mockX.ts` pattern |
| Routes | Route strings centralized in `App.tsx` or route config |

## 8. Import Rules

| Rule | Requirement |
| --- | --- |
| Types | Import from `src/types/index.ts` |
| Mock data | Import from `src/data/*` only in pages or API adapters |
| Components | Keep shared components free of page-specific imports |
| API client | Centralize network calls in `src/api/client.ts` |

## 9. Recommended First Build Order

| Step | Files |
| --- | --- |
| 1 | `main.tsx`, `App.tsx`, `index.css` |
| 2 | `types/index.ts`, `data/*` |
| 3 | Shared layout and cards in `components/*` |
| 4 | Route pages in `pages/*` |
| 5 | `api/client.ts` mock adapter |

## 10. Acceptance Checklist

| Check | Requirement |
| --- | --- |
| Clear separation | Fetch logic is not embedded inside presentational components |
| Contract stability | Types and mock data line up with API contract docs |
| Growth path | Folder structure can support later backend integration without refactor-heavy page rewrites |
