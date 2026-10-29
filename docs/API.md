# API and evidence data

All endpoints are same-origin under `/api`. Machine-readable OpenAPI is at `/api/openapi.json`; it requires authentication when tokens are configured. GET `/api/health`, `/api/ready` and `/api/session` are public. Errors use `{"detail": ...}` and responses carry `X-Request-ID`.

## Endpoints

| Method/path | Result |
|---|---|
| `GET /api/health` | Liveness, version, provider modes and stored case count |
| `GET /api/ready` | 200 if database and validated data are ready; 503 otherwise |
| `GET /api/session` | `auth_required,authenticated,role,reviewer,demo_enabled` |
| `POST /api/session` | `{token}` login, opaque session cookie |
| `DELETE /api/session` | Revoke browser session |
| `GET /api/dashboard` | Historical case-version counts grouped by recommendation/status/scrip/dealer |
| `GET /api/data` | Active dataset validation report and fingerprint |
| `POST /api/data/validate` | Validate a JSON bundle; always a report for structurally parseable JSON |
| `POST /api/data/import` | Validate, persist and activate a bundle; 201 or 422; does not start investigation |
| `GET /api/data/export` | Active dataset as JSON; includes audio metadata, not binary recordings |
| `POST /api/runs` | Submit investigation; 202 job, 409 if busy |
| `GET /api/runs?limit=50` | Latest-first durable job history; maximum limit 200 |
| `GET /api/runs/{id}` | One run, including progress, statistics or sanitized failure |
| `POST /api/run` | Compatible synchronous investigation; preserves reviews |
| `GET /api/stats` | Last successful investigation statistics |
| `GET /api/cases` | Ranked queue with filters and `X-Total-Count` |
| `GET /api/cases/{id}` | Full case, raw evidence, chart/transcript data and revision |
| `POST /api/cases/{id}/decision` | Atomic human decision with optional revision/idempotency |
| `GET /api/cases/{id}/export` | Downloadable case/evidence/audit JSON with integrity digest |
| `GET /api/export/cases.csv` | Filtered spreadsheet-safe queue export |
| `GET /api/ledger?limit=200&offset=0` | Ascending audit page, total and chain head |
| `GET /api/ledger/verify` | Chain verification, first bad sequence and reason |
| `POST /api/ledger/tamper-demo` | `{seq}` edit simulation; admin and `DW_DEMO=1` only |
| `POST /api/ledger/restore` | Destructive synthetic reset; admin and `DW_DEMO=1` only |
| `GET /api/eval?refresh=false` | Isolated labelled metrics; refresh requires admin; 409 without labels |
| `GET /audio/{call_id}?case_id={id}` | Archived recording used by that case, or 404 |

Queue filters: `q` (literal case-insensitive search), `status`, `recommendation`, `scrip`, `dealer_id`, `limit` (1–1000), `offset` (nonnegative). CSV accepts the same filters except paging. Recommendation order is ESCALATE, REVIEW, DISMISS; then descending score. IDs are stable opaque `CASE-...` strings: do not derive them from row numbers.

Admin and reviewer bearer tokens can also be sent via `Authorization: Bearer <token>`. Login is limited to ten attempts per minute per client address. Avoid putting a token into a URL or logs.

## Decisions

```json
{
  "action": "start_review",
  "reviewer": "Asha",
  "note": "Reviewed order timing and KYC link",
  "expected_revision": 0
}
```

Actions are `start_review`, `request_info`, `approve_escalation`, `dismiss`. Send `Idempotency-Key: <unique-request-id>` to safely retry a request after a network interruption. Preserve both the body and key for that retry. An already-used key with different data, a stale revision or a terminal-state change returns 409. In authenticated mode the configured server-side reviewer name overrides the body identity.

Example without configured authentication:

```bash
curl -s http://127.0.0.1:8077/api/cases
curl -s -X POST http://127.0.0.1:8077/api/runs
curl -s http://127.0.0.1:8077/api/ledger/verify
```

## Dataset bundle

Start with a download from the Data tab or `/api/data/export`; it is a complete import template. Required arrays are `dealers`, `persons`, `accounts`, `links`, `orders`, `trades`, `calls`. Use an empty array for an intentionally absent collection. `clauses`, `prices`, and `truth` are optional; absent clauses use checked-in reference data. An import never accepts arbitrary server filesystem paths.

| Record | Required fields |
|---|---|
| Dealer | `dealer_id,name,desk_phone,mobile,email` |
| Person | `person_id,name,relation,mobile,email` |
| Account | `account_id,holder_name,pan_masked,mobile,email,address,bank_account,device_id` |
| Link | `src,dst,kind,value,source` |
| Fund order | `order_id,scheme,scrip,side,qty,order_time,exec_start,exec_end,dealer_id` |
| Trade | `trade_id,account_id,scrip,side,qty,price,time` |
| Call | `call_id,dealer_id,counterparty_number,start_time,duration_s,utterances`; optional `audio_file` |
| Utterance | `id,speaker,start_ms,end_ms,text` |
| Price bar | `scrip,time,open,high,low,close,volume` |
| Clause | `clause_id,title,text,source_url` |

Market times must use complete ISO timestamps in **IST without offsets**, such as `2026-09-14T13:41:00`. Sides are BUY/SELL. Quantities are integer shares (1–10¹²); prices are finite INR numbers (0–10⁹ exclusive of zero). Limits are validation bounds, not realistic market assumptions. At most 250,000 rows per collection and a 32 MiB HTTP body by default. Call IDs use `C-` followed by 3–9 digits. Utterance identifiers are globally unique; offsets must fit call duration.

Link kinds: `shared_mobile`, `shared_email`, `shared_bank`, `shared_device`, `shared_address`, `declared_relative`, `called`. Endpoints reference an entity or an attribute node such as `phone:+919820011111`. Ground truth is `{"seed":7,"cases":[{"order_id":"...","account_id":"...","label":"TRUE_FR","expected":"ESCALATE","note":"..."}]}`. Labels support evaluation only and never decide recommendations.

Import saves normalized files under `runtime/datasets/<sha256>` and atomically switches a persisted active pointer. Re-importing identical content is idempotent. Imported JSON carries transcript/audio metadata; binary audio is not transferred. Existing case recordings remain available from their own archives.

## Export verification

An evidence JSON package contains `schema_version`, `case`, `evidence`, `ledger`, `disclaimer`, `exported_at` and `integrity`. Recompute `integrity.sha256` by removing the `integrity` key, JSON-encoding with sorted keys, compact separators, UTF-8 and `ensure_ascii=False`, and hashing those bytes. `ledger.verified` is the server's chain check at export time. Exported events are the relevant subset, so their sequence numbers can legitimately have gaps.
