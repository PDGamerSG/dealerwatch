# DealerWatch end-to-end design

The supplied repository is a synthetic front-running investigator for an Indian mutual fund house. Preserve the deterministic nine-link recommendation rules, grounded evidence, optional AI providers, and a basic offline-friendly frontend. The user authorized end-to-end implementation and parallel agents, with backend reliability taking priority over visual polish.

## Architecture and boundaries

Keep a single FastAPI application, SQLite persistence, and static HTML/CSS/JavaScript. No external service or API key is required in the default mock/replay mode. A bounded, single-worker background runner exposes durable job status; the synchronous `/api/run` remains compatible. This deployment intentionally uses one application worker. SQLite transactions serialize persistence across connections. The deterministic detector indexes time windows by scrip to avoid scanning all trades for every order.

Data enters as a JSON universe bundle or the repository's generated directory. Validate required files, model types, positive finite quantities/prices, timestamps and temporal consistency, identifiers, duplicates, references, audio paths, price bars, and optional evaluation truth. Imports create immutable content-addressed datasets under the runtime directory; invalid uploads never replace active data. Imports do not run investigations implicitly. Data is treated as synthetic/rehearsal input, not as a verified live market feed.

Investigation runs publish cases atomically after analysis. Ordinary reruns append audit events and preserve reviewer status/history with stable case identity. A case stores its dataset identity and evidence snapshot so later imports cannot rewrite old evidence. Failed runs leave prior cases and statistics intact. Human decisions use optimistic revision checks, idempotency keys, and an atomic case/audit transaction. Closed/escalated cases remain terminal.

The basic interface provides overview metrics, a searchable/filterable queue, existing evidence views, decisions, JSON evidence and CSV queue downloads, run progress/history, data validation/import, ledger verification and isolated evaluation. User text is inserted using safe DOM APIs. No CDN or frontend build step.

## API additions and shared interface

- `GET /api/dashboard`: `{cases, by_recommendation, by_status, total_profit_inr, by_scrip, by_dealer, latest_run}`; grouped collections are objects keyed by label, each with a count (scrip/dealer entries also carry profit).
- `GET /api/data`: validation report `{valid, counts, issues, fingerprint, source, date_range, label_counts}`. Issues have `severity`, `location`, `message`.
- `POST /api/data/validate`, `POST /api/data/import`: JSON universe bundle with `dealers, persons, accounts, links, orders, trades, calls`, optional `prices` (bar rows), `truth`. Validation returns a report; import returns a report and `imported: true`, or 422 for invalid input. `GET /api/data/export` downloads the active JSON bundle.
- `POST /api/runs`: returns HTTP 202 and a run object. `GET /api/runs` returns latest-first run objects; `GET /api/runs/{id}` returns one. Shape `{run_id,status,stage,completed,total,created_at,started_at,finished_at,stats,error}`, status is `QUEUED|RUNNING|SUCCEEDED|FAILED`. A concurrent submission returns 409. Jobs interrupted by a restart are marked failed.
- Existing `GET /api/cases` retains list response and adds `q,scrip,dealer_id,limit,offset` plus `X-Total-Count`. Existing detail remains compatible and adds `revision`, `dataset_id`, `run_id`.
- Decisions accept optional `expected_revision` and an `Idempotency-Key` header; stale writes return 409. Existing clients remain supported.
- `GET /api/cases/{id}/export` downloads a versioned JSON bundle including the case, raw evidence, relevant ledger events, and integrity digest. `GET /api/export/cases.csv` exports filtered queue data, escaping spreadsheet formulas.
- `GET /api/session`: `{auth_required,authenticated,role,reviewer,demo_enabled}`. Optional `DW_ADMIN_TOKEN` and `DW_REVIEWER_TOKEN` enable bearer-token authentication. `POST /api/session` accepts `{token}` and sets an HttpOnly SameSite cookie; `DELETE /api/session` logs out. Admin controls imports/runs/demo mutation; reviewer can read and decide. A configured reviewer identity is authoritative in authenticated mode. Default localhost demo mode stays usable without credentials. Mutations reject foreign Origin headers.
- `GET /api/ready` checks data validity and database availability; `/api/health` remains a lightweight liveness/configuration endpoint. Request IDs, bounded body sizes, sanitized failures, and safe response headers support operation.

## Core interfaces owned by persistence work

`pipeline.run(data_dir, runtime_dir, llm=None, *, reset=False, run_id=None, progress=None, dataset_id=None) -> RunStats`. `progress(stage: str, completed: int, total: int)` is optional. `reset=True` is reserved for explicit demo restoration/evaluation; normal runs preserve evidence and decisions.

`Case` gains defaulted `revision: int`, `dataset_id: str`, `run_id: str`, and `evidence_snapshot: dict`. Snapshot keys `trades`, `call_details`, `clauses`, `prices`, `node_labels` match existing detail fields. RunStats may gain optional run metadata with defaults. `apply_decision` retains its positional interface and adds optional keyword `expected_revision` and `idempotency_key`.

## Acceptance conditions

1. Existing detector, grounding, injection resistance, ledger, and API behaviors remain tested; intentional safe rerun changes are documented.
2. Planted true cases, weak evidence, coincidences, and at least three unlinked pattern decoys have the expected outcome. Evaluation reports finite, reproducible metrics and distinguishes the rules-only false positives.
3. Repeated runs cannot erase decisions, renumber existing cases, or partially replace cases on failure. Concurrent decisions cannot both finalize the same case; successful changes have a matching ledger record.
4. Invalid data, unsafe paths, stale revisions, unauthorized roles, foreign-origin mutations, oversized requests, and duplicate run submissions are tested.
5. UI actions exercise real API workflows with a headless browser test; offline mode completes without external requests or console errors. Layout is usable on desktop and mobile.
6. One command sets up seeded data and starts the app. Locked dependencies, environment example, container configuration, CI, architecture, API usage, demo walkthrough, and measured performance are documented.
7. Benchmark detector throughput on an expanded synthetic workload and record the actual environment and measurements. No unsupported production accuracy or performance claims.

## Deliberate limits

This is a hackathon rehearsal with synthetic data, a single process, and local SQLite. It does not connect to an exchange, submit regulatory filings, or prove misconduct. Hash chaining detects edits against the stored chain; a party with full disk control can replace the entire chain without an external checkpoint. Optional paid AI providers require user-supplied credentials and are not necessary for the working demo.
