# Step 6: deterministic Japanese document fields

The new entry point is `services.documentAnalysis.analyzer.analyze_ocr_document`.
It accepts an iterable of PaddleOCR 3.x prediction mappings (`rec_texts`,
`rec_scores`, `rec_boxes`, optional `rec_polys` and zero-based `page_index`).
No document type, filename, templates, manually entered keywords, network
services, or LLMs are consulted. Model inference and field extraction are separate.

```python
from services.documentAnalysis.analyzer import analyze_ocr_document

result = analyze_ocr_document(ocr.predict(document_path))
```

The engine itself uses only Python's standard library. `services.ocr.paddle_extractor`
provides a lazy image/PDF wrapper using the existing PP-OCRv6 Medium installation.
It requires the cached `PP-OCRv6_medium_det` and `PP-OCRv6_medium_rec` directories
under `~/.paddlex/official_models`, or an explicitly supplied model root. It does
not download replacement models. Low-confidence OCR boxes are retained rather
than removed by an inference confidence filter.

## Modules

- `services/ocr/records.py`: validate Paddle arrays and preserve source boxes,
  polygons, confidence, original array index, and page number.
- `fields/layout.py`: reconstruct horizontal rows and vertical Japanese columns,
  retain character-to-box provenance, and avoid joining across wide gutters.
- `fields/dates.py`: strict Gregorian and Reiwa/Heisei/Showa date parsing, including
  first-year notation and historical era boundaries. No missing-year inference
  or OCR digit repair.
- `fields/engine.py`: field labels, geometry, context checks, deduplication,
  document identification, and evidence-backed English output.

## Output contract

All generated prose, labels, reasons, statuses, and warnings are English.
Exact original Japanese occurs only in `evidence[].text`. Coordinates are in
Paddle's source coordinate system and are never rotated or scaled by this engine.
The inference wrapper disables orientation correction and unwarping. Original
array order is preserved as `originalIndex`, separately from `readingOrder`.
Each evidence item includes `id`, `text`, `confidence`, `bbox`, `polygon`, `page`,
`originalIndex`, and `readingOrder`. Page numbers are one based.

| Key | Meaning |
| --- | --- |
| `documentType` | Evidence-supported English type, or null |
| `summary` | Statements derived from verified fields, or null |
| `deadlines` | Labeled ISO dates, or null dates for unresolved labels |
| `amounts` | Integer JPY amounts and semantic roles, including unresolved values |
| `primaryDeadline` | A unique verified actionable date, or null |
| `primaryAmount` | A unique verified payment/billed/total/outstanding amount, or null |
| `importantPoints` | Statements derived from verified fields |
| `nextSteps` | Review the extracted deadline or verify specific uncertain fields |
| `evidence` | Every original OCR box, including irrelevant and low-confidence text |
| `warnings` | Uncertainty, conflicting evidence, and completed-payment notices |
| `extractionStatus` | `verified`, `partial`, `unverified`, or `no_fields` |
| `documentTypeEvidenceIds` | Sources supporting type identification or its conflict |
| `completedPaymentEvidenceIds` | Sources for explicit completed-payment statements |

Each deadline/amount contains an English `label`, semantic `kind`, `date`/`value`,
`status` (`verified` or `unverified`), `reasons`, `evidenceIds`, `ocrConfidence`,
`association`, and `occurrences`. Amounts also include `currency: "JPY"`.
A parsed candidate value can remain visible in an unverified entry; primary
fields and generated factual prose use verified entries only.

Verification requires valid syntax, a supported semantic label, bounded spatial
or textual association, no competing label with similar association strength,
no detected negative/conditional context, and adequate confidence in **all**
source boxes (default minimum 0.85). The confidence threshold is configurable;
it is not a probability that the extraction is correct. A bare number in a
neighbouring vertical column cannot establish a monetary amount.

Issue dates, receipt dates, billing periods, and scheduled debit dates are not
payment deadlines. Usage and validity expiration dates retain separate roles
and cannot become `primaryDeadline`. Date ranges remain unverified. Amounts
retain payment, billed, tax, late-fee, already-paid, total, and outstanding roles.
Generic or absent monetary labels do not establish payment roles. Only identical
values with identical roles, English labels, statuses, and reasons are merged;
they are never summed. Every source occurrence remains traceable through evidence.

Primary fields require agreement among all relevant candidate entries; unresolved
relevant labels also prevent selecting a primary field. Multiple genuine deadlines
remain in the list without choosing the earliest or first. An explicit completed-
payment statement suppresses `primaryAmount`; a historical already-paid amount
alone does not prove that an entire document has been settled. No procedures,
issuer identities, payment methods, or legal obligations are inferred.

`verified` means the extraction rules passed. It does not establish document
authenticity or independently confirm OCR accuracy. `partial` means some facts
passed while other fields remain unresolved; `unverified` means only unresolved
fields/conflicts were found; `no_fields` means no supported fields were found.
A document type alone can be a verified extracted fact. Unknown type does not
prevent independent field extraction.

## Validation

From the project root:

```sh
backend/.venv/bin/python -m unittest discover -s backend/tests -t backend -v
```

These synthetic tests use no Paddle, Django, Pydantic, AI packages, model downloads,
or private documents. An import-blocker test enforces that separation.

Optional real-image smoke test (defaults to `backend/test_documents/sample.jpg`):

```sh
backend/.venv/bin/python backend/try_ocr.py \
  --output "$HOME/ocr_private_test/step6-analysis.json"
```

An optional positional image/PDF path and `--model-root` are supported. Missing
input is an error. The runner never modifies the input or writes annotated images.
The optional JSON destination must be outside this workspace, must differ from
the input, and is given owner-only permissions. JSON contains all OCR evidence
and may contain personal information. `backend/test_documents/` and common OCR
output directories are ignored by Git. Do not commit private source documents,
logs, images, or extracted outputs.

## Integration boundary and limitations

Step 7 subsequently connects the upload route to this engine; see
[the backend integration contract](../../README.md). The notes below describe
Step 6's original isolation boundary. The field engine itself is unchanged.

Existing Django routes, Tesseract extraction, trusted-content templates, and the
legacy text-analysis function are unchanged. The old text endpoint still has its
existing AI fallback. It is not called or imported by the new Step 6 workflow;
Django integration and replacement of the old workflow are a separate task.
The new result intentionally differs from the legacy `DocumentAnalysisResultSchema`.

This engine is conservative and requires broader real-document evaluation before
production use. Unusual grids, overlapping/rotated text, missing labels, kanji
numerals, abbreviated or incomplete dates, stamps, and unrecognized wording may
remain unverified. Row/column reconstruction is geometric, not a general-purpose
layout model; it cannot always recover damaged documents or distinguish subtle
negation in unrestricted prose. This is extraction, not translation of the entire
document or verification of its authenticity. PDFs are delegated to PaddleOCR's
native page reader; synthetic multipage tests verify page separation, while the
optional local smoke test evaluates the available sample image.
