# DealerWatch handoff — 30 October 2026

Private repository: https://github.com/PDGamerSG/dealerwatch

Original source and retained Git history: https://github.com/Hydra-Of-Malice/dealerwatch-rehearsal

The original rehearsal is now an end-to-end application. Start with `uv run --frozen python -m dealerwatch`; open http://127.0.0.1:8077. Use `--audio --demo` for native synthetic speech and the explicit ledger demonstration.

Completed: durable investigations and evidence snapshots, archived audio, atomic decisions/audit, revisions/idempotency, background progress/history, validated immutable JSON imports, exports, optional admin/reviewer access, basic frontend workflows, native Mac/Windows audio, six repeated unlinked decoys, indexed detector, automated browser tests, lockfiles, CI and container configuration.

Current evidence: [EVAL.md](EVAL.md), [docs/VALIDATION.md](docs/VALIDATION.md), [detector benchmark](docs/validation/detector-benchmark.json). All 19 seed-7 labelled cases match expectations; escalation F1 is 1.000 versus 0.667 for the baseline. Detector median is 412 ms on 100k trades/1k orders in the recorded environment.

Operational details: [README](README.md), [architecture](ARCHITECTURE.md), [API contract](docs/API.md), [demo](docs/DEMO.md). The latest design in `docs/superpowers/specs/2026-10-30-dealerwatch-design.md` supersedes destructive rerun and demo-default details in the historical contract.

Release verification: 800 tests passed on Python 3.12; GitHub Actions also passed Python 3.13, browser and container jobs for commit `f7a501a`. The Linux ARM64 Docker image passed HTTP workflows, exports, audit verification and review/job persistence across restart; see [container evidence](docs/validation/container-smoke.json).

Remaining environment-dependent validation: real hosted LLM/Sarvam credentials and an installed Ollama model. These are optional integrations; the verified mock/replay application is complete without them. The hosted deployment is live at [Vercel](https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/) with the persistent AWS backend at `https://3.107.131.107`; it uses mock LLM/replay ASR and keeps demo mutations disabled. See [live validation](docs/VALIDATION.md) and [deployment operations](docs/DEPLOYMENT.md).

This remains a hackathon rehearsal. The repository's original event preparation, declared toolkit and day-of rebuild notes are preserved; see `DAY_OF_REBUILD.md` and `DECLARED_COMPONENTS.md` for those original rules. This implementation does not change event submission requirements.
