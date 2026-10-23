# Step 10 readiness report

Assessment date: 23 October 2026. **Code preparation: CONDITIONAL GO for controlled
validation. Public production: NO-GO until the operational gates below are met.**
No deployment, cloud purchase, Git commit/push, database reset or deletion of user
records was performed. The starting worktree was clean on `main`, one local commit
ahead of its configured upstream; that existing commit was preserved.

## Implemented improvements and evidence

| Area | Current implementation and evidence |
| --- | --- |
| Production settings | Separate base/development/production modules; production refuses missing/weak secret, debug opt-in, wildcard/development hosts, unsafe origins/proxy lists/private/public path overlap. Deployment checks ran with the actual production profile, installed Medium files, disposable migrated DB and 0600/0700 modes. |
| HTTPS/cookies/headers | Mandatory HTTPS redirect, trusted-peer-only forwarded TLS/IP handling, exact CORS/CSRF origins, secure HttpOnly Strict cookies, CSRF for session mutations, nosniff/frame/referrer/CSP restrictions. Tests cover trusted/untrusted proxy headers, hosts, CORS and CSRF failure. |
| OCR authorization | Active Django account plus explicit `models.analyze_document` permission; anonymous/invalid/expired/inactive/unprivileged requests fail before OCR. Production default DRF permissions are authenticated, with explicit public read-only routes. Public registration closed. |
| Account lifecycle | Existing token API repaired by installing its missing Django app; validated account inputs/password policy; login rotates token, fixed one-hour expiry, logout revocation. Browser token stays in RAM and old-account responses/results are discarded. |
| Rate/body/resource defense | Atomic private SQLite counters for IP and authenticated user, bounded counter capacity, fixed-window Retry-After, fail-closed store failure; pre-parser byte/charset checks; proxy rates/body/connection limits; existing one-child lifetime lease, one inference job, no job waiting queue, 120 s / 5 GiB guards and worker recycling. |
| Document handling | Allowed suffixes plus authoritative signatures/decoding, MIME disagreement rejection, restricted Pillow decoders, existing PDF/image/pixel/object/text limits. RAM upload buffers close across success, invalid data, interruption, timeout, memory error and busy failure. No new document persistence/public media route. |
| Auth/checklist database | Built-in auth/session/token migrations and additive app migrations tested on disposable SQLite. Category field now preserves the existing frontend input; IDs match its string contract. Old nonempty checklist rows survive migration. Two-account CRUD isolation and ignored client ownership IDs tested. |
| Backup/recovery | Consistent SQLite backup command, integrity verification, exclusive publication without overwrite, randomized temporary name and private modes. Disposable restore verified user/password, checklist, permission and repeatable migration state. Actual production backup scheduling/encryption remains manual. |
| Logging/privacy | Allowlist-only application and Gunicorn output, no native exception/stdout leakage, numeric proxy logs; secret/filename/request/exception sentinel tests. No external error reporter or analytics added. [Privacy/retention draft](18_privacy_retention_draft.md) reflects actual behavior. |
| Frontend | Live production build requires account UI and safe API URL; rejects mocks, localhost/HTTP/credential URLs, unknown `VITE_` keys and incomplete Vercel/CSP backend setup. Sign-in fits the existing layout; responsive decoder/English evidence/uncertainty and transient results remain intact. |
| Server preparation | One Gunicorn process/four threads, no preload, small backlog and header limits; example systemd unit adds memory/process/filesystem/network/core-dump controls and pre-start deployment/migration checks. Not installed or run under Linux/systemd. |

The known committed development signing key is no longer a production fallback.
If it was ever reused publicly, the operator must rotate it and revoke affected
sessions/tokens. Historical Git content is still public to repository readers;
this task did not rewrite Git history or silently delete account credentials.

## Tests and security checks

| Check | Actual result |
| --- | --- |
| Backend suite | 133 tests passed: existing 108 plus 25 targeted production/auth/migration/privacy cases |
| Frontend suite | 112 tests passed: existing 95 plus 17 configuration/auth/privacy cases |
| Frontend production build | Passed after dependency updates; TypeScript check included |
| Django normal system checks | Passed |
| Production deployment checks | No errors; two deliberate HSTS warnings, `security.W005` and `security.W021`; opt-in policy tests also pass with no warnings |
| Migration drift / dependency consistency | `makemigrations --check --dry-run`: no changes; `pip check`: no broken requirements |
| Migration application/restore | Applied from an older nonempty schema, repeated, backed up/restored and checked on disposable databases; real development DB unchanged |
| Python dependency audit | `pip-audit` 2.10.1: initially 82 advisory entries across five installed packages; after fixes, zero known vulnerabilities reported |
| JavaScript dependency audit | `npm audit`: initially five vulnerable dependency groups; after compatible updates, zero reported |
| Static security scan | Bandit 1.9.4 targeted production backend paths: zero findings; this is not a penetration test or an OS/native-library audit |
| Git whitespace check | Passed |

Python fixes: DRF 3.16.1 → 3.18.3, Pillow 12.1.0 → 13.0.0, AnyIO 4.12.1 → 4.15.1,
certifi 2026.1.4 → 2026.10.19, protobuf 6.33.4 → 6.33.5. Gunicorn 26.2.0 added.
Django remains 5.2.18; PaddleOCR 3.7.0 / PaddleX 3.7.2 / PaddlePaddle 3.2.0 and
Medium model settings are unchanged. JavaScript lockfile fixes include Vite 8.3.5,
Vitest/mocker 4.1.12, source-map-js 1.2.2 and undici 8.12.3. The direct Vite/Vitest
minimums were raised to those patched releases. Audits depend on advisory coverage
and the date queried; zero findings does not prove absence of vulnerabilities.

Production checks intentionally do not silence HSTS warnings. The default one-hour
HSTS duration applies to the backend host; including all subdomains/preload requires
verification and operator acceptance. Do not enable those flags merely to make a
check green. There were no debug, weak-key, cookie, missing-model or migration errors
in the tested production-like setup.

## Bounded runtime evidence

A real Gunicorn process using `config.settings_production`, a disposable account/DB
and actual local Medium models processed an explicitly synthetic 480×480 Japanese
image. Exact annotated date/amount roles were recovered. Login/access permission,
concurrent uploads (one 200, one 503), disconnect handling (another request got 503),
follow-up 200, readiness and server token revocation passed. At most one heavy child
was sampled; no upload-temp files remained, logs contained only allowlisted fields,
and development data was unchanged. The latest recorded run was approximately
8.23 s cold / 1.81 s warm, 883 MiB peak individual process and 991 MiB sampled service
RSS. An earlier run was 3.04 s cold / 0.60 s warm on this shared host, illustrating
that these were not controlled throughput comparisons. These small-image figures
are **compatibility/load-control evidence only**.
They cannot replace real-document sizing or establish production OCR accuracy.

A separate private Nginx 1.30.6 build used the prepared templates with only loopback
ports/private paths substituted and a disposable locally trusted certificate. Its
fake upstream test verified syntax, TLS certificate verification, CORS preflight,
foreign-origin rejection, no duplicate allowed-origin headers, authorization before
receiving a declared body (401/403), oversized-body 413, one active request with
concurrent 200/503, overwritten identity headers, numeric-only logs and zero body
files. Functional tests temporarily isolated rate timing; a fresh run with the
exact configured rate returned 401, 401, then 429. No system Nginx installation or
public listener was created. Linux and real certificate renewal remain unverified.

The dense-image smoke was stopped **before starting** by a conservative available-
memory preflight (about 3.7 GiB available on the shared Mac). It was not retried by
loosening that workload's 5 GiB preflight. The much smaller, explicitly separate
480×480 workload had its own 3 GiB preflight and the same runtime memory/time guards.
Step 9's real-document measurements remain about 4.2 GiB RSS and 9.6–9.8 s warm;
the synthetic PDF/size suite peaked around 4.30 GiB. Full-density and real-PDF
retesting after dependency changes is still a gate on the intended Linux host.

Detailed local aggregate artifacts remain outside Git. Reproduction helpers:

```sh
backend/.venv/bin/python backend/check_production_local.py --small-synthetic \
  --output "$HOME/ocr_private_test/step10/production-http-smoke.json"
# On Linux, add --font /absolute/path/to/a/Japanese-capable/font.ttf.
backend/.venv/bin/python backend/check_proxy_local.py \
  --nginx /absolute/path/to/nginx --openssl /absolute/path/to/openssl \
  --output "$HOME/ocr_private_test/step10/proxy-smoke.json"
```

These commands create disposable local test state and ephemeral loopback servers;
they do not deploy the application. The native helper requires sufficient available
memory and installed local models. Do not run native benchmarks in parallel.

## Remaining vulnerabilities, risks and manual gates

1. **Deployment identity and secrets:** configure real DNS/hosts/origins/CSP,
   independently generated production signing key, service user and private paths.
   Review historical key reuse and complete rotation/revocation if applicable.
2. **Linux runtime:** validate Python/Paddle native wheels and CPU compatibility,
   read-only model/cache behavior, one-model ownership, systemd/cgroup enforcement,
   client-disconnect behavior and full-density/multi-page memory on the selected VM.
   Mac RSS is not a verified Linux minimum. Provisional total budget is 7.5–9 GiB;
   8 GiB is conditional only. Prefer 12 GiB, or a 16 GiB tier, for initial validation.
3. **Public perimeter:** install/validate Nginx on Linux, verify proxy trust and
   HTTP framing, real TLS/renewal, CORS error/preflight headers, firewall and restricted
   administration. Application limiting is not a complete distributed-attack or
   slow-client defense. Shared NATs can also hit conservative IP limits.
4. **Accounts and data:** bootstrap an administrator, create pilot users and grant
   OCR explicitly; migrate the actual chosen DB after backup. No public self-service
   registration, account erasure/export UI, MFA or self-service password recovery
   was added. Use controlled administrator workflows until separately implemented.
   Token rows are stored by the existing DRF model and must be treated as credentials;
   encrypt backups and protect DB access.
5. **Retention/operations:** install backup/encryption/off-host recovery, log rotation,
   expired credential/counter maintenance, certificate/health/memory/rejection alerts
   and incident procedures. Proposed schedules are not active automations. Review
   swap/core/provider snapshots and any platform telemetry. The native child shares
   the application account and inherited environment; it is a resource boundary,
   not a separate privilege boundary. A parser compromise could therefore affect
   application data. Validation, process limits and the prepared OS sandbox do not
   eliminate this risk; assess stronger isolation before accepting hostile public
   uploads.
6. **Accuracy and sustained load:** the Step 9 accuracy corpus is only one partially
   annotated real document and eleven synthetic images. Step 10 adds a small synthetic
   compatibility smoke, not a representative real corpus. Full real false-positive
   rates/CER, diverse real PDFs, long-running allocator growth and multi-user sustained
   performance remain unknown. Preserve uncertainty; do not market payment advice
   or production accuracy from these tests.
7. **Database/scaling:** SQLite and the atomic local limiter fit a single low-write
   host; multiple hosts/containers require explicit coordination and likely a planned
   self-hosted PostgreSQL/shared limiter transition. Do not add web/model workers to
   an unmeasured memory budget. There is no durable OCR queue or automatic replay.

The [production guide](16_production_preparation.md) contains architecture, resource
allowances, verified published base-price examples, cost worksheet, environment,
startup, migration, HTTPS, backup and rollback procedures. An old anonymous release
must not be used as a public rollback target.

Code is ready for a controlled handoff and further staging validation. Operational
readiness remains **NO-GO for public deployment** until the listed gates are closed.
