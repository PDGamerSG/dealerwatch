# DealerWatch Implementation Plan

> **For agentic workers:** Implement the assigned independent area, verify it, and report concrete test evidence. The root agent integrates and reviews the complete workflow.

**Goal:** Deliver a reliable, runnable DealerWatch hackathon application with a basic frontend and complete evidence/review workflow.

**Architecture:** FastAPI serves vanilla JavaScript and a SQLite-backed investigation service. Validated immutable data snapshots feed deterministic investigation runs, grounded narratives, and auditable human decisions. A bounded background runner supports asynchronous work.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, SQLite, NetworkX, NumPy, native HTML/CSS/JavaScript; pytest and Playwright for verification.

**Spec:** `docs/superpowers/specs/2026-10-30-dealerwatch-design.md`

## Global constraints

- Basic frontend; backend reliability is the priority.
- Keep existing dependencies for runtime; optional browser tooling is development-only.
- No network in Python tests, secrets in source/logs, automatic escalations, or HTML insertion of untrusted strings.
- Preserve existing nine-link recommendation rules and deterministic seed-7 behavior.
- Agents own disjoint files; integrate through the documented interfaces. Do not commit or push shared work from agents.
- Mock/replay must run without credentials. Document provider and deployment limits honestly.

## Task 1: Durable investigation core

Files: `dealerwatch/models.py`, `store.py`, `pipeline.py`, `decisions.py`, optional new persistence helper modules, `tests/test_persistence.py`.

- [x] Write failing tests for rerun preservation, failure atomicity, decision concurrency, stale revision and idempotency; run them.
- [x] Add stable identities, evidence snapshots and atomic publication, preserving existing model compatibility.
- [x] Make human decisions and their audit append atomic; add revision and idempotency checks.
- [x] Implement documented progress callback and run metadata.
- [x] Run persistence, core and existing pipeline tests; report commands and results.

## Task 2: Synthetic scenarios and performance

Files: `dealerwatch/data/synth.py`, `dealerwatch/detect/sandwich.py`, `scripts/make_audio.py`, new generator/audio tests and `scripts/benchmark.py`.

- [x] Add failing tests for unlinked pattern decoys, deterministic generator, referential integrity, and indexed detector equivalence.
- [x] Generate at least three high-score unlinked decoys that recommend REVIEW, preserving existing cases.
- [x] Index detector trade windows without changing boundary semantics or score output.
- [x] Add native macOS speech rendering with safe subprocess argument arrays and retain Windows support.
- [x] Test, benchmark representative expanded data, and report measurements.

## Task 3: Application services and API

Files: `dealerwatch/api.py`, new `datasets.py`, `jobs.py`, `security.py`, `exports.py`, corresponding API tests.

- [x] Write and run failing validation/import, job and authorization API tests.
- [x] Implement bounded validation, immutable import/export and persisted active-dataset selection.
- [x] Implement background jobs, restart recovery and conflict rejection, integrating pipeline progress.
- [x] Add role-based optional authentication, origin checks, request limits, request IDs and readiness.
- [x] Expose dashboard/filtering, versioned evidence exports and safe CSV export.
- [x] Retain compatibility with existing endpoints; isolate eval and destructive demo reset.

## Task 4: Basic functional frontend

Files: `dealerwatch/web/index.html`, `app.js`, `style.css`.

- [x] Preserve existing evidence and review interface.
- [x] Add basic overview, data validation/import, search/filter/export, asynchronous run progress/history and optional session controls using documented API shapes.
- [x] Respect revisions, user roles, errors, empty states and keyboard/mobile use; keep all dynamic text safe.
- [x] Run JavaScript syntax checks and report frontend verification requirements.

## Task 5: Setup, integration and handoff

Files: `README.md`, `ARCHITECTURE.md`, `docs/DEMO.md`, `docs/API.md`, `docs/VALIDATION.md`, `.env.example`, `requirements.lock`, container/CI definitions, launch scripts and browser tests.

- [x] Run full pytest and a real HTTP smoke workflow against generated data.
- [x] Exercise all main frontend actions in a headless browser, including import errors, run progress, review, exports, ledger and evaluation.
- [x] Review security/concurrency/failure paths, fix findings, and rerun affected checks.
- [x] Produce current evaluation and performance evidence, reproducible setup and demo instructions.
- [x] Confirm clean dependency installation and startup; leave the application locally available with a concise handoff.
