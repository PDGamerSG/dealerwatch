<div align="center">

# DealerWatch

### Evidence-grounded front-running investigations for fund compliance teams

[![CI](https://github.com/PDGamerSG/dealerwatch/actions/workflows/ci.yml/badge.svg)](https://github.com/PDGamerSG/dealerwatch/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-3776ab)](https://www.python.org/)
[![Frontend](https://img.shields.io/badge/frontend-Vite%20%2B%20React-646cff)](https://vite.dev/)
[![Demo](https://img.shields.io/badge/demo-live-1f883d)](https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/)

Detect trade sandwiches, connect calls to account relationships, and give a reviewer a case file they can defend.

[Open the landing page](https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/) · [Open the console](https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/app) · [Read the demo script](docs/DEMO.md)

</div>

DealerWatch is a working hackathon prototype for investigating possible front-running around fund orders. It joins order and trade timing, account relationships, recorded-call transcripts, evidence clauses, and reviewer decisions in one workflow. The repository contains a FastAPI backend, a durable SQLite runtime, a basic static console, and a separate Vite landing page. The seeded dataset is synthetic and contains no customer records.

## Why this project matters

Compliance teams often have the right evidence in different systems. An order blotter shows the fund order, a trade feed shows activity around it, KYC systems show relationships, and call recordings contain the context. Joining those records by hand takes time and makes the final decision difficult to audit.

DealerWatch turns that join into a repeatable case workflow. Deterministic rules identify candidate sandwiches. Relationship and call stages add context. A grounding check keeps generated text tied to evidence. A reviewer makes the final decision, and a hash-chained ledger records what happened.

The application is designed for a demo and a controlled synthetic evaluation. It is not a claim about live-market accuracy.

## Three steps to a case

1. **Run the pipeline.** The seed-7 dataset produces 19 labelled cases with planted positive, review, and dismiss scenarios.
2. **Open a case.** The queue shows the order timeline, linked accounts, call transcript, evidence chain, clauses, audio, and current recommendation.
3. **Review and record.** A human can request information, approve escalation, or dismiss the case. The decision, revision, and audit event persist across reruns.

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```bash
git clone https://github.com/PDGamerSG/dealerwatch.git
cd dealerwatch
uv run --frozen python -m dealerwatch
```

Open <http://127.0.0.1:8077>. The first start creates the seed-7 synthetic data, validates it, investigates it, and serves the API and console. Existing runtime data and reviews are preserved.

To generate native synthetic speech and enable the explicit ledger demonstration controls:

```bash
uv run --frozen python -m dealerwatch --audio --demo
```

Audio is optional. Replay transcripts and the complete investigation workflow work without external credentials or network access after dependencies are installed.

## Hosted build

The public landing page and console are served by Vercel. The persistent backend runs as one Docker worker on AWS so that SQLite databases, archived audio, imported datasets, and run history remain on disk.

| Surface | Link |
|---|---|
| Landing page | [dealerwatch-pallab-das-projects-d3f377fd.vercel.app](https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/) |
| Reviewer console | [dealerwatch-pallab-das-projects-d3f377fd.vercel.app/app](https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/app) |
| Backend readiness | [3.107.131.107/api/ready](https://3.107.131.107/api/ready) |
| Deployment guide | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

## What it does

| Stage | Behavior |
|---|---|
| Detect | Uses indexed time windows to find same-side activity before a fund order and opposite-side activity after it. Repeat count, timing, and matched profit contribute to the candidate score. |
| Gather | Finds dealer calls in the lookback window when the caller is connected to the trading account through declared relationships. |
| Extract | Replays a stored transcript or calls the optional speech and language-model adapters. Extracted leak cues must cite real utterances and ground their numbers. |
| Link | Builds a dealer-to-account graph from shared phone, email, bank, device, and declared relationship attributes. |
| Verify | Checks a nine-link evidence chain covering the order, trades, profit, pattern, link path, call, cue, and applicable clause. |
| Explain | Produces a short evidence-cited summary. A deterministic template replaces output that fails the grounding checks. |
| Review | Lets a named reviewer request information, approve escalation, or dismiss a case. The application never escalates a case by itself. |
| Record | Stores case snapshots, immutable audio references, run progress, revisions, decisions, exports, and a hash-chained audit ledger. |

## How it works

```text
synthetic orders + trades + KYC links + call records
                         │
                         ▼
                  indexed detector
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
       link graph    call window   price/profit
           └─────────────┼─────────────┘
                         ▼
                 grounded evidence chain
                         │
                         ▼
              reviewer queue and case file
                         │
                         ▼
                 decision + audit ledger
```

The backend is a single-tenant FastAPI service. SQLite stores the case, job, and ledger databases. The pipeline publishes a case and its audit event atomically, uses revisions for optimistic concurrency, and keeps review decisions when a case is rerun. The browser console talks to the documented API in [docs/API.md](docs/API.md).

## Results on the seeded evaluation

The labelled seed-7 universe contains 19 scenarios: 6 expected escalations, 10 reviews, and 3 dismissals. DealerWatch matched all 19 expected recommendations. Escalation precision, recall, and F1 were 1.000, 1.000, and 1.000. The trade-score baseline reached 0.500 precision, 1.000 recall, and 0.667 F1 because it escalated six unlinked repeated-pattern decoys.

The indexed detector processed 100,000 trades and 1,000 orders in a 412 ms median benchmark on the recorded Mac environment, with the same 7,107 candidates as the previous scan. The benchmark excludes data generation, disk I/O, speech recognition, and language-model latency.

Read the generated [EVAL.md](EVAL.md) and the fresh [validation record](docs/VALIDATION.md) for commands, environments, and limits.

## Security and data handling

- The repository ships synthetic names, accounts, trades, calls, and prices only.
- Transcript text is treated as untrusted data and is inserted into the DOM as text.
- Grounding checks reject citations and numbers that do not exist in the evidence snapshot.
- Partial evidence produces `REVIEW`; only a reviewer can change a case to `ESCALATED`.
- State-changing requests use same-origin checks, body limits, expiring sessions, and optional administrator or reviewer tokens.
- The ledger records a canonical payload hash and previous hash for every event.
- API keys are read from environment variables and are never written to reports or the runtime database.

## Known limits

- The dataset is synthetic. Production use would need approved order, trade, KYC, and recording feeds.
- The current link graph uses exact shared attributes. Fuzzy name and address matching is future work.
- Rules and replay transcripts are tuned for the included English dealer-desk scenarios.
- Optional OpenAI, Anthropic, Ollama, and Sarvam adapters have deterministic fallbacks. Their live quality and latency were not measured without credentials or a local model.
- SQLite is intentionally deployed as one worker on persistent storage. The AWS deployment guide explains the backup and restart requirements.

## Verify locally

```bash
uv sync --frozen
uv run --frozen pytest -m '' -q
uv run --frozen ruff check .
node --check dealerwatch/web/app.js
node --test scripts/test_vercel_build.mjs
uv run --frozen python -m dealerwatch --check
uv run --frozen python -m dealerwatch.eval.harness --runtime runtime/evaluation-cli --md EVAL.md
cd landing
npm ci
npm run typecheck
npm run build
```

The CI workflow repeats the Python 3.12 and 3.13 suites, the Chromium browser workflows, the Vercel output test, the container smoke test, and the landing-page typecheck/build.

## Repository map

| Path | Purpose |
|---|---|
| `dealerwatch/` | FastAPI application, pipeline, persistence, API models, exports, and evaluation harness |
| `toolkit/` | Generic ledger, provider adapters, ASR replay, and grounding helpers |
| `dealerwatch/web/` | Basic static reviewer console and self-hosted fonts |
| `landing/` | Vite and React marketing page with the 3D evidence-chain visual |
| `data/` | Synthetic source data definitions and generated-data tooling |
| `scripts/` | Vercel packaging, benchmark, container, deployment, and development helpers |
| `tests/` | Unit, API, security, persistence, evaluation, and browser tests |
| `docs/` | API contract, architecture, demo script, deployment runbook, and validation evidence |

## Development and deployment

Run the basic console with `./scripts/dev.sh`. Use `cd landing && npm install && npm run dev` when working on the landing page. The container path is:

```bash
docker compose up --build
```

For a hosted build, set `DW_BACKEND_URL` in Vercel to the HTTPS AWS origin and keep the SQLite runtime on the persistent AWS host. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the exact environment variables, backup procedure, and read-only live checks.

## Submission package

The HackIn Drive 2026 material is kept in the repository so the team can review it before submitting:

- [Team details](TEAM.md)
- [₹50,000 budget](BUDGET.md)
- [Video script, pitch outline, and form copy](PITCH.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)
- [Current handoff](HANDOFF.md)
- [Declared components](DECLARED_COMPONENTS.md)

The source repository is public. Do not commit `.env.local`, runtime databases, generated local data, provider keys, or deployment bypass tokens.
