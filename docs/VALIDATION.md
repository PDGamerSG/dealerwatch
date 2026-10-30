# Verification record — 30 October 2026

Environment: macOS 27.0.1 arm64, Apple M1 Max (10 logical CPUs), Python 3.12.14, uv 0.12.13, Chromium 156.0.8078.4. All application tests use mock LLM and replay ASR unless explicitly testing provider failure adapters. No hosted inference credentials were needed.

## Automated checks

| Check | Evidence |
|---|---|
| Original baseline | 637 tests passed before changes |
| Complete Python + real browser suite | `uv run --frozen pytest -m '' -q`: 749 passed on Python 3.12.14; a fresh source-only copy with locked dependencies also passed all 749 on Python 3.13.15 |
| Default Python suite | 747 tests; browser tests separately selected with `-m browser` |
| Static checks | `uv run --frozen ruff check .`, `node --check dealerwatch/web/app.js`, `git diff --check` |
| Dependency reproducibility | Fresh temporary Python 3.12 environment installed only `requirements.lock`; seeded data validated and real FastAPI HTTP workflow returned 19 cases and a valid 98-entry ledger. Fresh Python 3.13 source-only installation passed CLI data validation and the complete 19-scenario evaluation |
| Container | Compose validation, a clean Linux ARM64 image build, and `python3 scripts/check_container.py --image dealerwatch:release-check --output docs/validation/container-smoke.json` passed with Docker Engine 29.9.2 |
| Real local server | Readiness, ranked queue, case detail, exact evaluation links, evidence export, archived WAV and chain verification passed at port 8077 |

Meaningful regressions cover failure-atomic publication, independent-connection decision races, revision conflicts, idempotent retries, existing-schema migration, WAL rejection, immutable audio, changed-evidence and changed-recommendation versions, non-finite persistence rejection, import fingerprint round trips, invalid data, malformed/oversized/chunked requests, session roles, foreign-origin mutations/evaluation, throttling, background concurrency, restart recovery and evaluation isolation.

The two Chromium workflows start their own temporary servers. Desktop tests exercise filters, all four review actions, terminal states, evidence/CSV/dataset downloads, validated imports, background reruns preserving decisions, ledger tamper/restore, and evaluation links. Authenticated mobile tests exercise role controls, reviewer attribution, all navigation tabs, session revocation, and horizontal overflow in both case and evaluation views. The default flow records no browser application/console errors or external requests.

## Synthetic outcome evaluation

`uv run python -m dealerwatch.eval.harness --data data/generated --runtime runtime/validation-eval --md EVAL.md`

Seed 7: 19/19 recommendations correct, 6 escalation recommendations, 10 reviews, 3 dismissals. DealerWatch escalation precision/recall/F1 are 1.000/1.000/1.000; the trade-score baseline is 0.500/1.000/0.667. Six high-scoring unlinked repeated patterns create the baseline's false escalations. The planted prompt-injection transcript does not alter the expected result. An additional data-agent sweep across seeds 0–49 checked all 950 planted outcomes, including 300 decoys.

The generator deliberately avoids accidental background sandwiches. These results validate designed scenarios and the evidence workflow; they are not an estimate of live-market false-positive rates. See [EVAL.md](../EVAL.md).

## Performance

Detector benchmark command:

```bash
uv run python scripts/benchmark.py --orders 1000 --trades 100000 --repeat 3 --output docs/validation/detector-benchmark.json
```

The seeded, independently generated workload has 600 accounts, eight symbols and 20 trading days. Both implementations produced 7,107 identical full Candidate objects. Parsing and indexing are timed; dataset generation, disk I/O, ASR and LLM calls are excluded. Each algorithm has one untimed warmup followed by three measured runs.

| Detector | Runs (ms) | Median (ms) |
|---|---|---:|
| Indexed windows | 399.725, 447.464, 411.871 | 411.871 |
| Previous symbol scan | 6402.389, 6252.420, 6270.977 | 6270.977 |

Measured median ratio: **15.23×**. [Raw benchmark JSON](validation/detector-benchmark.json) includes environment, workload digests and result digest.

A separate real Uvicorn loopback check used 30 sequential requests per endpoint against the 19-case dataset with audio:

| Endpoint | Median | p95 |
|---|---:|---:|
| Health | 1.19 ms | 1.34 ms |
| Queue | 5.55 ms | 5.85 ms |
| Case detail | 3.85 ms | 4.26 ms |
| Dashboard | 5.22 ms | 5.46 ms |

These are local observations, not a throughput/SLA guarantee. [HTTP smoke report](validation/http-smoke.json).

## Audio and optional environments

Ten recordings were rendered on this Mac using installed Rishi/Lekha voices. WAV validation confirmed mono, 16-bit, 16 kHz audio and utterance offsets inside each recording. The live API returned an archived 1,071,272-byte WAV for the first escalation case.

Live OpenAI/Anthropic/Sarvam generation and transcription were not exercised without credentials. Ollama is installed but has no local model; real local-model quality/latency was not measured. Provider adapters, grounding checks and fallback behavior have automated tests. GitHub Actions is configured for Linux Python 3.12/3.13, Chromium and Docker; the repository's Actions page records remote results separately from these local measurements.

The built Linux ARM64 image ran as UID 10001 with all capabilities dropped and a disposable named data volume. Real HTTP checks verified automatic seeding/investigation, packaged frontend assets and reference clauses, all 19 expected recommendations, idempotent human review, a background rerun preserving the review, evidence SHA-256, CSV/dataset exports and a valid 197-entry ledger. After a container restart, the case decision, job history and audit chain remained intact. The temporary container and volume were removed. [Container verification report](validation/container-smoke.json).

## Operation left available

Start the application with `uv run --frozen python -m dealerwatch` at http://127.0.0.1:8077. Default startup keeps destructive demo controls off unless `--demo` or `DW_DEMO=1` is supplied. The release repository is [PDGamerSG/dealerwatch](https://github.com/PDGamerSG/dealerwatch) (private); the original rehearsal Git history is retained. The hosted handoff is documented in [DEPLOYMENT.md](DEPLOYMENT.md).

## Vercel/AWS deployment

The release changes passed **800 Python/browser tests**, two Node build-output tests, Ruff, JavaScript syntax and diff checks. GitHub Actions passed for Python 3.12/3.13, browser workflows, and container checks on commit `f7a501a`. The package inspection confirmed that local environment files, runtime databases and generated data were excluded. A new Linux ARM64 image passed real HTTP review, rerun, export, audit and restart-persistence checks.

The AWS Compose configuration passed validation for persistent host mounts, nonroot backend, one replica and secure cookies. Caddy 2.11.7 issued a publicly trusted short-lived certificate for the static IP. The live read-only checker passed all 12 checks through both AWS and Vercel: readiness, authenticated access, 19 cases, evidence and CSV/dataset exports, SHA-256 evidence integrity, 98-entry ledger verification, run history, dashboard totals, and evaluation links. Restarting the backend preserved the reviewed case, 9 completed runs, and the intact audit chain. Seven archived WAV recordings passed Vercel playback, format, and SHA-256 checks. The disposable `DW_DEMO=1` remote desktop/mobile workflows passed 2/2 tests; a final hardened reviewer workflow passed with demo mutations disabled.

The Vercel `dealerwatch` project is linked and aliased to [dealerwatch-pallab-das-projects-d3f377fd.vercel.app](https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/). Live AWS provisioning, public TLS issuance, proxying, audio, authentication, workflow, and persistence checks are complete. See [deployment instructions](DEPLOYMENT.md) and the live reports in `docs/validation/`.
