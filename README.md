# DealerWatch

An end-to-end front-running investigator for a mutual fund compliance team. It connects order and trade patterns, dealer relationships, recorded-call evidence, grounded explanations, and human review. This repository is a **hackathon rehearsal using synthetic data**.

The backend uses FastAPI, SQLite, NetworkX and Python. The intentionally basic frontend uses HTML, CSS and JavaScript with no build step, CDN or external asset dependency; it shares the landing page's ink-and-paper palette and ships Archivo and IBM Plex Mono as self-hosted subsets under `dealerwatch/web/fonts`. The default demo requires no API keys or network connection after installation.

## Start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), clone the private repository using an account with access, then run:

```bash
git clone https://github.com/PDGamerSG/dealerwatch.git
cd dealerwatch
uv run --frozen python -m dealerwatch
```

Open **http://127.0.0.1:8077**. The command installs locked dependencies, creates the seed-7 synthetic dataset if missing, validates it, investigates it on first startup, and serves the API and frontend. Existing data and reviews are preserved. Python 3.12 is selected by `.python-version`.

macOS/Linux convenience launcher, including optional `.env` loading:

```bash
./scripts/dev.sh
```

To add native synthetic speech on macOS or Windows and enable the ledger demonstration controls:

```bash
uv run --frozen python -m dealerwatch --audio --demo
```

Audio is optional; transcript-based investigation works on every supported platform. macOS uses installed `say` voices and `afconvert`; Windows uses SAPI. The generated speech, names and accounts are fictional.

If you use pip instead:

```bash
python3.12 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.lock
python -m dealerwatch
```

## Working features

- Deterministic BUY/SELL sandwich detection with indexed time windows, matched-quantity profit and repeat-pattern scoring.
- Dealer-to-account graph analysis using declared relationships and shared KYC attributes.
- Call gathering, transcript replay or optional speech recognition, grounded leak-cue extraction, and citation-checked summaries.
- Nine-link evidence verification. Complete evidence recommends escalation; partial evidence goes to review. **Only a human reviewer changes a case to ESCALATED.**
- Searchable investigation queue, price/trade timeline, transcript and audio playback, evidence links, clauses, decision history, overview and run history.
- Background investigations with stage/progress reporting, bounded concurrency, durable status and restart recovery.
- Atomic case/audit updates, optimistic revisions, idempotent decision retries, immutable evidence/audio snapshots, and preserved reviews across reruns.
- JSON dataset validation/import/export, CSV queue export, and versioned JSON evidence packages with SHA-256 integrity digests.
- Optional administrator/reviewer authentication, expiring browser sessions, same-origin mutation checks, body limits and login throttling.
- Hash-chain verification, explicitly enabled tamper/reset demonstrations, and evaluation isolated from live investigations.

## Demo and measurements

Seed 7 generates 40 fund orders, 2,558 trades, 60 accounts, 25 calls and 60,000 price bars. All **19 labelled scenarios** produce the expected recommendation: 6 ESCALATE, 10 REVIEW, 3 DISMISS. The six unlinked repeated-pattern decoys expose false escalations in the trade-score baseline.

| Synthetic evaluation | DealerWatch | Trade-score baseline |
|---|---:|---:|
| Escalation precision | 1.000 | 0.500 |
| Escalation recall | 1.000 | 1.000 |
| Escalation F1 | 1.000 | 0.667 |
| All-label accuracy | 19/19 | 9/19 |

These are controlled synthetic results, not production accuracy estimates. See [EVAL.md](EVAL.md), [validation evidence](docs/VALIDATION.md), and the [three-minute demo](docs/DEMO.md).

On the recorded Mac benchmark, the indexed detector processed 100,000 trades and 1,000 orders in **412 ms median**, versus **6,271 ms** for the previous scan, with 7,107 identical candidates. This measures detection only, not hosted model or speech-service latency. Reproduce with:

```bash
uv run python scripts/benchmark.py --orders 1000 --trades 100000 --repeat 3
```

## Verify

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
node --check dealerwatch/web/app.js
uv run playwright install chromium
uv run pytest -m browser -q
uv run python -m dealerwatch --check
uv run python -m dealerwatch.eval.harness --runtime runtime/evaluation-cli --md EVAL.md
```

Python tests use temporary databases and no external services. Browser tests start isolated local servers and cover review, escalation, dismissal, reruns, imports/exports, ledger verification/tamper/restore, evaluation, authentication and mobile layout. CI runs Python tests on Linux 3.12/3.13, Chromium workflows, and a container build with HTTP and restart checks.

The evaluation runtime must be isolated. The harness refuses a live application runtime or existing review history. The demo's **Restore clean ledger** action intentionally clears cases and decisions and is available only with `DW_DEMO=1`; ordinary runs preserve history.

## Configuration and operation

Copy `.env.example` to `.env` and launch with `./scripts/dev.sh`, or use `uv run --env-file .env python -m dealerwatch`. Raw `python`/`uvicorn` commands read process environment variables, not `.env` automatically.

| Setting | Default | Purpose |
|---|---|---|
| `DW_DATA` | `data/generated` | Source evidence directory |
| `DW_RUNTIME` | `runtime` | Cases, ledger, archived audio, jobs, imported datasets and evaluation caches |
| `DW_LLM` | `mock` | `mock`, `ollama`, `openai`, `anthropic` |
| `DW_LLM_MODEL` | Provider default | Exact installed/available model name |
| `DW_ASR` | `replay` | `replay` or `sarvam` |
| `DW_DEMO` | `0` | Enables destructive ledger demonstration controls |
| `DW_ADMIN_TOKEN`, `DW_REVIEWER_TOKEN` | Unset | Distinct operator access tokens; either enables authentication |
| `DW_PUBLIC_ROLE` | Unset | `reviewer` lets anonymous visitors review cases while admin actions keep requiring the administrator token |
| `DW_MAX_BODY_BYTES` | `33554432` | 32 MiB upload limit |

Optional external providers retain deterministic fallbacks if unavailable. Hosted models need their own API keys; Sarvam needs `SARVAM_API_KEY`. The current local machine has no Ollama model installed, so live provider quality/latency is not part of the verified offline results.

Run **one application worker per runtime directory**. Keep the case and ledger databases in SQLite rollback journal mode; attached transactions use SQLite's super-journal for atomic commits. Do not enable WAL for these two databases. Back up the complete runtime directory while the server is stopped, together with the original source dataset. Restore that complete set, then verify the ledger.

Local mode without tokens grants administrator access and binds to loopback. For network use, configure distinct tokens, TLS, an appropriate reverse proxy, and `DW_COOKIE_SECURE=1`; add `DW_PUBLIC_ROLE=reviewer` only when the console should open to the public as a reviewer, as the hosted synthetic demo does. The application is a single-tenant hackathon system, not a production financial surveillance deployment.

## Landing page

`landing/` holds a standalone, scroll-driven marketing page for DealerWatch built with Vite, React Three Fiber and GSAP. It has no backend dependency and uses only synthetic figures. See [landing/README.md](landing/README.md). The hosted site serves it at [dealerwatch-pallab-das-projects-d3f377fd.vercel.app](https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/) with the reviewer console at `/app`.

```bash
cd landing && npm install && npm run dev
```

## Container

```bash
docker compose up --build
```

Compose binds to loopback and keeps data in a named volume. The container runs as a non-root user with a readiness health check. The Linux ARM64 image passed startup, frontend/API, review, rerun, export, audit and restart-persistence checks. Reproduce the container check with:

```bash
docker build --tag dealerwatch:check .
python3 scripts/check_container.py
```

The check uses its own temporary container and volume, then removes both. See the [recorded result](docs/validation/container-smoke.json).

See [architecture](ARCHITECTURE.md), [API and data contracts](docs/API.md), [current handoff](HANDOFF.md), and the original [rehearsal contract](CONTRACT.md). The original hackathon preparation and day-of rebuild notes remain in the repository.

## Hosted deployment

The [Vercel and AWS deployment guide](docs/DEPLOYMENT.md) describes the frontend proxy and a persistent single-worker backend. The repository includes Vercel build configuration, AWS container/HTTPS configuration, and reusable live HTTP/browser checks. Vercel functions must not host the SQLite runtime on temporary disk.
