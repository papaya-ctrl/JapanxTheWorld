# Step 15: free Linux x86_64 PaddleOCR verification

Prepared 31 October 2026. **Workflow prepared and locally validated; GitHub workflow
NOT EXECUTED. Linux native OCR import/inference and performance remain unverified.**
Nothing was committed, pushed, dispatched, deployed or purchased in this step.

The user reports that Step 14's actual Ubuntu ARM64 authenticated non-OCR API
checks passed. That environment intentionally cannot verify PaddleOCR. This step
prepares a separate, manually selected Linux x86_64 runner without changing that
working environment or the production/frontend/authentication architecture.

## Repository inspected

At inspection, the local branch was `main`, HEAD `b617a5f` (Step 13). Live
`git ls-remote origin refs/heads/main` returned
`9bcd675964d1c448f3f1860737919858286c7615`, matching cached `origin/main`.
Local history is **five commits ahead**, including Steps 9–13; GitHub's main does
not yet contain that implementation. Step 14's settings/dependency/tests/docs
remain uncommitted. No existing `.github/workflows/` directory was present.

Ignored local `.env` files, venv, SQLite databases, `.local-staging`, private
document directory, Python caches, `dist` and `node_modules` were identified by
path, without copying their contents. No private fixtures, actual env files or
databases appeared in the tracked candidate-file inventory; tracked `.env.*.example`
files are examples. This is an inventory, not a guarantee about every historical
blob: review **all five outgoing commits**, not only this workflow, before publishing.

Files reviewed include the main/dev requirements, OCR configuration/worker/adapter/
resource guards, evaluation and regression suites, model installer, existing
synthetic fixtures, and the Step 9/11/13/14 benchmark/staging/pilot documentation.

## Workflow configuration and cost boundary

`.github/workflows/linux-x86-ocr.yml` has exactly one event: `workflow_dispatch`.
It runs only for a public repository, on standard `ubuntu-24.04`, with Python 3.12,
`contents: read`, a 30-minute timeout and one repository-wide concurrency group.
Verification runs do not overlap. Checkout/setup-python are pinned
to inspected official action commits, with no persisted checkout credentials.
There is no push/PR/schedule trigger, self-hosted/larger/GPU runner, Docker build,
dependency/model cache action, artifact upload, deployment step or extra secret.

GitHub currently documents the public standard Linux runner as 4 CPUs, 16 GB RAM,
14 GB SSD and x64, with standard public-repository runner usage free. These are
documented specifications, **not observations from an executed job**.
[Runner specifications](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[billing boundary](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
The job deliberately skips private repositories; do not change its runner label or
visibility guard to obtain an assumed free run. No artifact/cache storage is requested.

Before heavy downloads, the preflight publishes distro, kernel, x86_64 architecture,
Python, available/total RAM, CPU counts, free disk, cgroup v1/v2 limits/current/peak
counters and selected commit/image identity. It requires native Ubuntu 24.04,
Python 3.12, four available CPUs, AVX, at least **8 GiB effective available RAM**
(including ancestor cgroup restrictions) and **8 GiB free disk**. Inadequate capacity
fails explicitly. These admission thresholds are test safeguards, not a measured
minimum for deployment.

## Dependency installation

The workflow consumes **existing `backend/requirements-dev.txt`**, including the
unchanged main pins and utilities needed by the synthetic regression suite and
official model installer. Relevant unchanged pins:

| Dependency | Version |
| --- | --- |
| PaddlePaddle CPU | 3.2.0 |
| PaddleOCR | 3.7.0 |
| PaddleX | 3.7.2 |
| Pillow | 13.0.0 |
| pypdfium2 | 5.14.0 |
| psutil | 7.2.2 |
| Django / DRF | 5.2.18 / 3.18.3 |

Local PyPI metadata inspection found matching Python 3.12 Linux x86_64 wheels for
all 18 direct main/dev pins, including
`paddlepaddle-3.2.0-cp312-cp312-manylinux1_x86_64.whl`. A metadata-only cross-platform
`uv pip compile` resolved **79 runtime packages**, with binary-only selection and
no local dependency installation. This proves a resolver plan, not Linux linking,
installation or inference. [Paddle wheel index](https://pypi.org/project/paddlepaddle/3.2.0/#files),
[official CPU installation documentation](https://www.paddleocr.ai/v3.5.0/en/version3.x/paddlepaddle_installation.html).

On the actual runner, pip first resolves with `--dry-run --ignore-installed
--only-binary=:all:`. `ci/linux_ocr.py` inspects every resolved filename against the
runner's native compatible tags, verifies the project pins and a SHA-256 for every
wheel, and rejects source distributions, GPU/LLM packages and missing/incompatible
wheels. The install then uses the inspected exact pins/hashes with `--no-deps
--require-hashes`; it does not independently resolve a different set. `pip check`
and the recorded installed distribution versions follow. No `paddlepaddle-gpu`,
CUDA, torch, transformer model, LLM or external OCR service is requested.

If resolution fails, the exact pip `ERROR:` dependency lines are printed and the
job stops before inference. There is no version/model downgrade, source-build
fallback or fabricated passing result. Pip uses PyPI without an extra index or
cache. Some wheels may need downloading during pip's metadata resolution when
their index lacks separate metadata; the compatibility gate remains mandatory.
Ubuntu installs only Japanese Noto CJK fonts and required CPU shared libraries.

## Actual inference gate prepared

The existing official installer is called explicitly with `--size medium`, into
new runner-temporary storage. It resolves the official `PP-OCRv6_medium_det` and
`PP-OCRv6_medium_rec` repository revisions and records downloaded file hashes.
Resolved revisions/hashes appear in the inference summary, not model files.
Upstream heads are resolved at run time, as in the existing installer; this is
not a frozen model-weight lock or proof of identical Mac/Linux weights.

A supervised subprocess first imports native Paddle/PaddleOCR and rejects a CUDA
build. That is an **import gate only**. It does not count as model initialization
or inference. The separate inference phase runs the existing `LocalDocumentWorker`,
local Paddle constructor, image adapter and verified field engine unchanged:

- Medium detection + Medium recognition, batch 1, four threads, detector side 1600,
  static CPU engine, MKLDNN disabled.
- Existing 5 GiB worker RSS cap, 120-second request timeout, sampled RSS/headroom
  cancellation and single-worker lease. No parallel OCR or unbounded stress loop.
- One cold request and two warm requests on the same in-memory synthetic Japanese
  image, with actual positive model-init and inference-call measurements required.
- Independently specified payment deadline, separate usage expiration, verified
  payment amount, Japanese labels/evidence links, English generated output,
  null primary amount and partial extraction status. Missing/wrong results fail.
- Warm runs must reuse the same worker and report zero new model-init time.
  Production schema validation checks source evidence references; raw predictions
  are never filled in, printed or saved.

The fixture is the existing explicitly synthetic insurance-tax-like test image:
payment deadline 2031-06-30, expiration 2032-06-30, payment 5,000 yen, unknown total.
It is generated specifically during the run with Noto Japanese glyphs. No input
path, private document, real tax slip or user annotation can be supplied to this
CLI. The inference phase uses local model directories and HF offline mode; the
existing constructor refuses missing files instead of downloading replacement models.

The full backend regression suite runs before model download. It covers the
existing English/Japanese evidence contract, verified/unverified/null/partial
behavior, date roles, upload bounds and fail-closed authentication/permission,
token/CSRF/account-isolation cases. Its mocked/structured OCR cases are not counted
as actual native inference; that evidence comes only from the later three requests.

## Measurements, cleanup and public output

The job summary is the runtime Markdown report. It identifies each gate as passed,
failed or NOT RUN and includes the inspected wheels/hashes, installed versions,
model revisions/hashes, model-init time, cold/warm request times, inference-call
counts, sampled worker peak RSS, sampled cgroup current peak, kernel cgroup lifetime
peak when available, failure code and worker cleanup result. Unavailable metrics
remain JSON `null`; unexecuted gates remain NOT RUN. Byte counts and seconds are
explicit. Cgroup ancestors can include other job processes, and kernel peaks are
lifetime values, not reset/inference-only peaks.

Heavy subprocess groups also stop on 1 GiB effective available-memory headroom,
6 GiB aggregate process-group RSS, 2 GiB remaining disk, 10 MiB captured logs, or
their bounded command timeout. The native worker's own stricter 5 GiB cap remains.
Before each request, an additional 3 GiB available-memory check runs. Limits are
sampled safeguards, not protection against every instantaneous native allocation.
Timeout/failure cleanup terminates the subprocess group; native workers close in
`finally`. The final always-run cleanup removes generated models, caches, temporary
files and unpublished native/test logs. Runner disposal handles residual state
after a hard job cancellation; always steps cannot be guaranteed after VM loss.

Only explicit generated status/numeric files enter `$GITHUB_STEP_SUMMARY`. No raw
OCR text, result JSON, image/PDF, annotation, password/token, model weights/cache or
raw regression/native logs are uploaded as artifacts. Synthetic fixture expected
values live in source; no private data is required. Reported regression counts are
the runner's actual unittest count, not the local count copied into a success field.

## Current results and comparison limits

| Evidence | Status in this preparation session |
| --- | --- |
| Workflow configuration | Prepared; actionlint 1.7.12 passed |
| New guard/wheel/report/verifier unit tests | 14 passed on macOS ARM64; mocked/structured inputs only |
| Existing full backend regression suite | 199 passed on macOS ARM64; isolated test DBs |
| Real CLI refusal/cleanup/summary plumbing on this Mac | Passed: wrong OS/architecture refused, only marked generated state removed, failed/NOT RUN gates preserved |
| Direct pin wheel metadata / full cross-platform binary resolution | Passed metadata checks; 18 direct pins / 79 resolved runtime packages |
| GitHub workflow execution | **NOT RUN — awaits user review/commit/push/dispatch** |
| Linux x86_64 distribution/CPU/RAM/disk/cgroups | **NOT OBSERVED** |
| Linux dependency installation / native imports | **NOT RUN** |
| Linux model initialization / real OCR / field results | **NOT RUN** |
| Linux cold/warm time / worker RSS / cgroup peak | **UNMEASURED** |
| Linux cleanup behavior under real native load | **NOT VERIFIED** |
| Production-like dense/PDF/load/resource validation | **NOT VERIFIED** |
| Public production readiness | **NO-GO; existing gates remain** |

The historical dense Mac baseline is approximately 4.2 GiB worker RSS, 10.8 seconds
cold and 9.6–9.8 seconds warm (Apple M4, macOS, different dense private input).
The Step 11 small synthetic Mac baseline is about 877 MiB, 2.62 seconds cold and
0.56 seconds warm, also a different fixture. The prepared Linux fixture is small;
neither baseline supports a controlled speedup, sizing ratio or accuracy comparison.
Once executed, compare observed Linux values descriptively alongside their runner,
model revisions and workload. GitHub-hosted CPU/storage contention and hardware
differ from both the Mac and a final VPS. Three small serial requests cannot
establish representative PDF latency, sustained throughput, long-run leaks, kernel
OOM behavior, real-document accuracy or safe final hosting capacity.

Remaining blockers are the actual user-triggered run and its results, any wheel/
native/model incompatibility it exposes, representative dense/PDF Linux resource
validation, independently reviewed diverse real-document accuracy, production
TLS/secrets/backups/monitoring and the prior production-readiness gates. A green
smoke workflow alone does not resolve those blockers.

## Exact review and publication commands — user action only

Run from the Mac checkout root. First review outgoing history and local changes:

```sh
git status --short
git status --short --ignored
git log --oneline origin/main..HEAD
git diff --check
git diff -- backend/README.md backend/.gitignore backend/config/settings_base.py \
  backend/controllers/document_controller.py backend/controllers/readiness_controller.py \
  docs/19_linux_staging.md docs/20_staging_readiness_report.md
cat .github/workflows/linux-x86-ocr.yml ci/linux_ocr.py ci/test_linux_ocr.py
cat backend/staging_tools/verify_linux_ocr.py docs/25_linux_x86_ocr_verification.md

PYTHONPATH=backend:. backend/.venv/bin/python -m unittest ci.test_linux_ocr
backend/.venv/bin/python backend/manage.py test tests --verbosity 0
# If actionlint is installed:
actionlint .github/workflows/linux-x86-ocr.yml
```

After reviewing Step 14 and Step 15, stage **only** this explicit source/docs list.
Do not use `git add .`, `git add -A` or `git add -f`. A new review branch retains the
five local preceding commits; inspect their complete diff too.

```sh
git switch -c codex/linux-x86-ocr-verification
git add -- backend/.gitignore backend/README.md backend/config/settings_base.py \
  backend/config/settings_local_staging.py backend/controllers/document_controller.py \
  backend/controllers/readiness_controller.py backend/requirements-arm64-staging.txt \
  backend/tests/test_local_staging.py docs/19_linux_staging.md \
  docs/20_staging_readiness_report.md docs/24_arm64_local_staging.md \
  .github/workflows/linux-x86-ocr.yml ci/linux_ocr.py ci/test_linux_ocr.py \
  backend/staging_tools/verify_linux_ocr.py docs/25_linux_x86_ocr_verification.md
git diff --cached --check
git diff --cached --name-only
git diff --cached
git diff --stat origin/main
git log --stat origin/main..HEAD
```

Inspect every staged new Step 14 file too, including the settings and tests. After
checking that only intended source/docs and public examples are included:

```sh
git commit -m "ci: prepare manual Linux x86_64 PaddleOCR verification"
git log --oneline origin/main..HEAD
git push --set-upstream origin codex/linux-x86-ocr-verification
```

**The preceding commit/push commands are instructions for you; Codex did not run
them.** On GitHub, review the branch/PR including all outgoing commits and merge it
into default branch `main` when ready. Do not force-push or replace remote main.
If GitHub has advanced, fetch/reconcile normally and review the changed diff first.
The workflow must exist on the default branch before its first manual dispatch;
GitHub documents this requirement in
[manually running workflows](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

Only after that review/merge, manually execute:

```sh
gh workflow view linux-x86-ocr.yml --repo papaya-ctrl/JapanxTheWorld
gh workflow run linux-x86-ocr.yml --repo papaya-ctrl/JapanxTheWorld --ref main
gh run list --repo papaya-ctrl/JapanxTheWorld --workflow linux-x86-ocr.yml \
  --event workflow_dispatch --limit 5 --json databaseId,headSha,status,conclusion,url
```

Choose the returned run ID whose `headSha` matches the reviewed merged commit.
Replace the literal `RUN_ID` below with that numeric ID:

```sh
gh run watch RUN_ID --repo papaya-ctrl/JapanxTheWorld --exit-status
gh run view RUN_ID --repo papaya-ctrl/JapanxTheWorld --web
```

Read the job summary's separate import/inference/regression/cleanup gates, not only
the run's green check. A skipped job, a successful environment/import step, or a
report step run after failure is not a passed inference test. Record the run URL,
commit, actual package/model versions, field checks, timings, memory and limitations
in a new dated results addendum only after execution. No result is prefilled here.
