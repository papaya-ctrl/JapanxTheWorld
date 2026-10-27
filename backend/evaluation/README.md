# Private, reproducible OCR evaluation

Step 12 adds a strict independent-annotation schema, encrypted artifacts, explicit
precision/recall and failure denominators, frozen OCR replay, and error-stage review.
Use the [current workflow](../../docs/21_accuracy_evaluation_workflow.md) and
[measured results](../../docs/22_document_accuracy_report.md) for new evaluation.
The commands below document the original Step 9 schema and historical comparisons.

Run from the project root using Python 3.12 and `backend/requirements-dev.txt`.
Evaluation runs local PaddleOCR and deterministic Python, serially, without paid
AI calls. Never run native profile benchmarks alongside API smoke tests or another
benchmark: the CLI comparison runner owns one child per profile and is intended
for controlled offline evaluation. The API worker separately uses its global lease.

## Dataset and independent annotations

Create eleven explicitly synthetic images covering eight categories, with extra
vertical, blurred and rotated variants. Existing files/annotations are never
overwritten. Supply `--font /absolute/path/font.ttf` with Japanese coverage on
platforms without the default macOS Arial Unicode font.

```sh
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.fixtures \
  "$HOME/ocr_private_test/new-dataset" \
  --private-sample backend/test_documents/sample.jpg
```

The optional real sample is referenced without modification. It starts
**unannotated**: edit its private manifest using facts reviewed from the original
document, not predictions from the analyzer. The Step 9 measured manifest was
annotated separately using previously user-specified known facts. Its private
facts are intentionally absent from the generator. Do not reuse old predictions
as ground truth or silently change annotations to improve scores.

The framework accepts up to fifty documents per run, with explicit provenance
`synthetic`, `real_private` or `anonymized_real`. Keep images, transcriptions,
annotations and results outside the workspace. Each item in schema version 1's
`documents` array has this structure (all values below are synthetic examples):

```json
{
  "id": "R002",
  "path": "/private/evaluation/document.png",
  "category": "utility",
  "provenance": "anonymized_real",
  "variant": "clean",
  "groundTruth": {
    "complete": true,
    "documentType": "Electricity Notice",
    "deadlines": [
      {"kind": "payment", "date": "2031-06-30", "label": "Payment deadline"}
    ],
    "amounts": [
      {"kind": "billed", "value": 5000, "label": "Billed amount"}
    ],
    "primaryDeadline": "2031-06-30",
    "primaryAmount": 5000,
    "extractionStatus": "verified",
    "transcription": "independently transcribed source text"
  }
}
```

IDs must be unique `[A-Z][0-9]{3}`. Categories are `national_health_insurance`,
`residence_tax`, `national_pension`, `utility`, `school`, `employment`, `municipal`,
and `unknown`. Unknown document type is null. Omit unannotated optional keys rather
than marking them null: null explicitly asserts that no primary field/type should
be selected. Mark `complete: false` for partial field annotation. Add
`annotationSource` privately to describe review/provenance.

Date and amount matches require both the semantic kind and exact ISO date/integer
value. Duplicates of the same role/value count once. Only verified predictions
count as positive fields. Complete annotations allow exact-set accuracy and
false-positive counts; partial annotations allow known-field recall only, with
false-positive/exact scores null. Unverified candidates remain separately counted.
Optional exact English label scoring covers matched fields only, so always read
it with recall. Optional document type, primary fields and extraction status score
only when annotated. CER uses NFKC/whitespace normalization over reconstructed
evidence order; exact edit distance is bounded to 5000 reference / 10000 output
characters. Missing transcription is unscored, not zero errors.

## Profiles and guarded benchmarks

Medium models must already be installed under `~/.paddlex/official_models` or
`--model-root`. The selected API defaults do not change the frozen old profile.
The baseline profile captures the installed Step 8 defaults: Medium/Medium,
batch6, CPU10, requested MKLDNN and detector1920; actual backend/version metadata
is recorded. To compare original adapter code as well, run it before applying
pipeline changes, as in Step 9. Source fingerprints are retained privately.

Optional Small models are installed explicitly from official PaddlePaddle
repositories; this utility is never called by requests:

```sh
backend/.venv/bin/python backend/download_ocr_models.py
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.runner \
  "$HOME/ocr_private_test/new-dataset/manifest.json" \
  --profiles baseline-medium,medium-cpu4,small-small,small-medium,medium-small \
  --output "$HOME/ocr_private_test/model-comparison"
```

Run tuning separately with `--profiles medium-side1792,medium-side1600,medium-cpu2`.
`medium-batch1` and `medium-batch2` vary only the baseline recognition batch. Batch2
was not measured in Step 9. Use `--ids R001 --repeat 3` for three sequential known
sample requests, or `--max-documents 50` when thirty to fifty real images become
available. Profiles run in manifest order; the first selected document is cold,
subsequent ones warm. At most five repeats and 1000 total requests are allowed.
Choose small bounded runs; those maxima are capacity bounds, not a stress-test
recommendation.

The runner records elapsed/model-init/inference time, page count/time, child and
parent RSS, available host memory, swap growth, predictor/backend classes and
package versions. It samples RSS every 50 ms. Default stop guards: 120 s/request,
6144 MiB child RSS (old baseline replay only), 768 MiB minimum host available,
512 MiB swap growth. Host-pressure failure stops the entire run. To replay selected
production sizing, pass `--max-rss-mib 5120`. Never relax guards to finish a failing
run. The machine and background workload affect measurements.

`metrics.json` and optional `--save-private-predictions` files remain outside Git
and use owner-only permissions. The latter contains sensitive evidence and is
off by default. Standard output includes only fixed IDs, timings, profile names
and allowlisted outcome codes; native child output is suppressed. Inputs are
checked unchanged after every request. No request logs include raw source text.

## PDF/size and API load checks

```sh
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.load_cases \
  "$HOME/ocr_private_test/new-dataset"
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.runner \
  "$HOME/ocr_private_test/new-dataset/load/manifest.json" \
  --profiles medium-side1600 --max-rss-mib 5120 \
  --output "$HOME/ocr_private_test/pdf-size-check"
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.load_api \
  "$HOME/ocr_private_test/new-dataset/manifest.json" \
  --output "$HOME/ocr_private_test/api-load.json"
```

The generated suite has eight cases: one/three scanned pages, embedded Japanese
text, a 14.85 MP image, a near-10 MiB image, corruption, excessive bytes and excessive
pages. Expected errors count as accepted rejections, not unexpected failures. The
API check submits only two synthetic inputs concurrently and one follow-up,
asserting one busy response and correct request association. Its temporary throttle
override is confined to that process. Timeout/memory tests use controlled fake
workers and small budgets, not host exhaustion.

## Publish aggregates and verify

```sh
PYTHONPATH=backend backend/.venv/bin/python -m evaluation.report \
  "$HOME/ocr_private_test/model-comparison/metrics.json" \
  "$HOME/ocr_private_test/pdf-size-check/metrics.json" \
  --output docs/local_benchmark_aggregate.csv
backend/.venv/bin/python backend/manage.py test tests
npm test
npm run build
```

The publisher allowlists aggregate fields, profile names and provenance; paths,
document IDs, raw text, predictions, annotations and exception details are excluded.
Review the generated aggregate before sharing. Blank scores mean unscored. The
Markdown [Step 9 report](../../docs/15_ocr_optimization_benchmark.md) explains the
actual dataset, controlled failures, model decisions and limits. Eleven synthetic
images and one partial real sample cannot establish broad extraction accuracy.
