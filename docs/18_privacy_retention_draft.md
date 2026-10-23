# Privacy and retention draft — Step 10

Draft dated 23 October 2026. This describes the implemented application and prepared
configuration. It is not a legal-compliance determination or a promise that an
unconfigured hosting provider behaves this way. The operator must complete the
retention, hosting, contact and backup choices below before publication.

## What the application processes

The Document Decoder receives a JPEG, PNG, WebP or PDF, checks bounded format/size/
page/pixel limits, and runs local PaddleOCR and deterministic Python rules. It does
not send documents to a paid AI service or local LLM. Original Japanese text and
bounding boxes appear as source evidence only in the requesting user's response;
English labels and uncertainty indicators explain the extracted fields. A verified
field is an extraction-rule result, not proof that a document is authentic or that
OCR is correct.

Production requires a signed-in, active account explicitly authorized for OCR.
Account and checklist requests use the authenticated Django user, not a frontend
user ID. One account cannot list, edit or delete another account's checklist items.
Anonymous legacy checklist rows are inaccessible in production. Administrators with
appropriate server/database privileges can access stored account/checklist data;
this is not end-to-end encryption.

## Storage and retention behavior

| Data | Implemented handling |
| --- | --- |
| Upload bytes and parsed images/PDFs | Bounded RAM buffers in the active decoder path; no permanent upload file/database record; released after completion/error/interruption |
| OCR text, dates, amounts and evidence | Returned to the current request; not written to database/logs by this flow |
| Browser analysis results | Memory only; cleared on reload, new decoder flow or account change; no result in persistent browser storage/navigation history |
| Account credentials in the browser | Password sent to login; short-lived token in memory only; expires after one hour; no token in Vite configuration or local/session storage |
| Server account data | Username, optional email/name, password hash, permissions and account status in private SQLite until operator-managed account retention/deletion |
| API tokens and admin sessions | Private Django/DRF tables; tokens have a fixed one-hour authentication lifetime, rotate at login and are revoked on successful logout; expired rows need periodic cleanup |
| Checklists | User-entered title/category/due date/completion stored for that account until deletion/operator retention; not automatically populated from OCR |
| Rate counters | Bounded private SQLite counters keyed by HMACs, without raw IP/user identifiers; expired windows removed during later limiter activity; idle residual rows can remain until maintenance |
| Operational metrics | Allowlisted time, category/status/error code, duration and RSS; no request body, filename, account ID, IP, credentials or OCR text |
| Backups | Operator-created private DB snapshots can contain accounts, tokens, sessions, checklists and any pre-existing legacy records; require encryption and a retention schedule |

The old application had document/analysis persistence models and a legacy writer.
The live decoder bypasses them, regardless of the legacy raw-text flag. Existing
historical records, if present in another database, are not silently deleted by
Step 10. Review such records privately and establish a deliberate retention policy.
Local development/demo settings can expose a shared anonymous checklist and mock
checklist storage; they must not be used as a public production service.

## Temporary data and disconnections

Django's decoder uses a memory-only upload handler and explicitly closes buffers
for successful, invalid, timed-out, memory-limited, overloaded and interrupted
requests. Native parsers and inference run in a supervised subprocess. Model
allocators may retain RAM until reuse, idle exit or request-count recycling; this
is not guaranteed memory erasure. An already-running job may finish after a client
disconnects, bounded by the same time/memory guards. No automatic duplicate OCR
request is made.

The prepared proxy authorizes before body buffering and keeps supported OCR bodies
in a bounded RAM buffer. Its fallback temporary directory is private and outside
public paths. Linux validation of this proxy/service configuration remains pending.
The operator must also control swap, crash/core dumps, provider snapshots, browser
extensions, reverse-proxy tooling, analytics and third-party logging. Application
RAM-only processing alone cannot rule out all disk traces or provider access.

## Cookies, access and external services

The SPA uses an explicit in-memory Authorization token with browser cookie
credentials omitted. Django admin/session clients retain CSRF protection and
production secure, HttpOnly, SameSite Strict cookies. A successful logout revokes
the server token and clears local results; if the network prevents revocation, the
UI clears local state and explains that server revocation could not be confirmed.
The credential still expires within its fixed lifetime. Signing in again revokes
the account's previous token.

A static frontend host, VPS provider, domain/DNS/TLS and any chosen backup service
are separate operators. Their network metadata, billing, access and retention
policies must be reviewed before selection. No hosting/backup account was connected
or resource purchased in this preparation. Model weights are downloaded explicitly
from official repositories during setup, independently of uploads; normal decoder
requests do not download models or make paid AI calls.

## Operator decisions before publishing

- Identify the responsible operator, contact address, hosting regions/providers and
  any processors; write the actual account/deletion and incident-response process.
- Establish account/checklist retention and a way to handle a user's deletion or
  export request without exposing another user's records. No new self-service
  account-erasure/export UI was implemented in this task.
- Configure numeric-log retention (proposed seven days), expired session/token/rate
  cleanup, and encrypted backup retention (proposed seven daily/four weekly copies).
  These are proposals, not installed schedules. Do not delete active files or locks.
- Document how deletion propagates to retained encrypted backups and how restoring
  an older backup avoids reactivating revoked credentials or deleted records.
- Verify HTTPS, header handling, encryption/keys, access grants, monitoring and
  backup recovery. Do not enable request-body capture or session replay.
- Explain extraction limitations and advise users to confirm important information
  with the issuing organization. The real-document evaluation corpus is too small
  to establish production accuracy.

Replace this draft with an operator-reviewed policy matching the deployed system.
No legal or regulatory compliance certification is claimed.
