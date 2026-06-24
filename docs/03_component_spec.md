# JapanxTheWorld Component Specification

## 1. Shared Component Rules

| Rule | Requirement |
| --- | --- |
| Styling | White background, blue primary color, small red accent, rounded cards |
| Accessibility | Buttons and inputs must have visible labels and focus states |
| Typography | Clear headings, short paragraphs, easy scanning |
| Reuse | Shared props and styles should prevent duplicate page logic |
| Responsiveness | Stack vertically on mobile, expand to grid/rows on larger screens |

## 2. Component Catalog

| Component | Purpose | Used on |
| --- | --- | --- |
| `Navbar` | Main navigation | All pages |
| `Footer` | Footer links and trust note | All pages |
| `FeatureCard` | Homepage feature summary card | Home, Student-to-Worker |
| `DocumentInputForm` | Collect document analysis input | Document Decoder |
| `AnalysisResultCard` | Display decoder result | Document Result |
| `UrgencyBadge` | Show urgency level visually | Document Result |
| `ImportantPointsList` | Show key extracted points | Document Result |
| `NextStepsList` | Show action items | Document Result |
| `GuideCard` | Show guide summary | Life Guides |
| `ChecklistItem` | Single checklist row | Dashboard |
| `OfficialResourceCard` | Show trusted link information | Help Center, Guide Detail |

## 3. Props And States

### `Navbar`

| Item | Spec |
| --- | --- |
| Props | `links: { label: string; to: string }[]` |
| States | desktop, mobile menu open, active route |
| Behavior | Collapsible menu on mobile, active link styling |
| Accessibility | `nav` landmark, keyboard-accessible toggle |

### `Footer`

| Item | Spec |
| --- | --- |
| Props | Optional `supportNote?: string` |
| States | static |
| Behavior | Show official confirmation reminder and copyright area |
| Accessibility | Semantic footer and descriptive link text |

### `FeatureCard`

| Item | Spec |
| --- | --- |
| Props | `title`, `description`, `ctaLabel`, `ctaTo`, `accent` |
| States | default, hover |
| Behavior | Entire card or CTA button links to target page |
| Accessibility | Clear heading hierarchy and descriptive CTA |

### `DocumentInputForm`

| Item | Spec |
| --- | --- |
| Props | `initialValue?`, `onSubmit`, `isSubmitting`, `errorMessage?` |
| Fields | `documentText`, `documentTypeHint`, `sourceLanguageHint` |
| States | idle, validation error, submitting |
| Behavior | Validate required text or file placeholder before submit |
| Accessibility | Input labels, helper text, error text tied to fields |

### `AnalysisResultCard`

| Item | Spec |
| --- | --- |
| Props | `result: DocumentAnalysisResult` |
| States | default, no deadline, related guide available |
| Behavior | Render source-neutral result layout using the shared result schema |
| Accessibility | Sections with headings and list semantics |

### `UrgencyBadge`

| Item | Spec |
| --- | --- |
| Props | `urgency: "low" | "important" | "urgent"` |
| States | low, important, urgent |
| Behavior | Color and label change by urgency |
| Accessibility | Must not rely on color alone; text label required |

### `ImportantPointsList`

| Item | Spec |
| --- | --- |
| Props | `items: string[]` |
| States | populated, empty fallback |
| Behavior | Show bullets or numbered cards for key points |
| Accessibility | Use list markup |

### `NextStepsList`

| Item | Spec |
| --- | --- |
| Props | `steps: string[]` |
| States | populated, empty fallback |
| Behavior | Ordered list with action-focused copy |
| Accessibility | Use ordered list markup |

### `GuideCard`

| Item | Spec |
| --- | --- |
| Props | `guide: GuideSummary` |
| States | default, hover |
| Behavior | Show title, short summary, category, estimated time |
| Accessibility | Entire card or CTA must be keyboard accessible |

### `ChecklistItem`

| Item | Spec |
| --- | --- |
| Props | `item: ChecklistItem`, `onToggle`, `onEdit`, `onDelete` |
| States | incomplete, complete, editing, saving error |
| Behavior | Checkbox/toggle plus action buttons |
| Accessibility | Checkbox semantics, button labels for edit/delete |

### `OfficialResourceCard`

| Item | Spec |
| --- | --- |
| Props | `resource: OfficialResource` |
| States | default |
| Behavior | Show title, category, short description, external link |
| Accessibility | External links must announce destination clearly |

## 4. Example Type Shapes

```ts
type FeatureCardProps = {
  title: string;
  description: string;
  ctaLabel: string;
  ctaTo: string;
  accent?: "blue" | "red";
};

type DocumentInputFormValues = {
  documentText: string;
  documentTypeHint?: string;
  sourceLanguageHint?: string;
};
```

## 5. Visual System Conventions

| UI element | Rule |
| --- | --- |
| Cards | White surface, blue border accent or shadow, rounded corners |
| Alerts | Red accent for urgent/error, blue accent for info, amber accent for important warning |
| Buttons | Primary blue fill, secondary white fill with blue border |
| Lists | Comfortable spacing and short items |
| Empty states | Friendly explanation plus one suggested action |

## 6. Loading And Error Expectations

| Component | Loading UI | Error UI |
| --- | --- | --- |
| `DocumentInputForm` | Disabled submit and spinner text | Inline form error |
| `AnalysisResultCard` | Skeleton card or placeholder blocks | Page-level retry block |
| `GuideCard` list | Repeated skeleton cards | Banner with retry button |
| `ChecklistItem` list | Spinner or subtle loading message | Inline mutation failure message |
| `OfficialResourceCard` list | Skeleton cards | Retry banner |

## 7. Accessibility Checklist

| Check | Requirement |
| --- | --- |
| Color contrast | Badges and buttons meet accessible contrast |
| Keyboard support | Menus, links, buttons, form controls fully keyboard usable |
| Labels | Inputs must not rely on placeholder text alone |
| Headings | Page and card headings follow a clean hierarchy |
| Status updates | Loading/error messages should be screen-reader friendly |

## 8. Build Order

| Order | Components |
| --- | --- |
| 1 | `Navbar`, `Footer`, `FeatureCard` |
| 2 | `UrgencyBadge`, `ImportantPointsList`, `NextStepsList` |
| 3 | `DocumentInputForm`, `AnalysisResultCard` |
| 4 | `GuideCard`, `OfficialResourceCard`, `ChecklistItem` |
