# Three-minute DealerWatch rehearsal

Start: `uv run --frozen python -m dealerwatch --demo`. For optional native speech use `--audio` before beginning. All records are synthetic. No API key is needed.

1. **0:00–0:30 — Problem and overview.** Open Overview. Explain that fund orders, retail trades, KYC relationships and recorded calls usually live apart. The seeded universe produces 19 investigation cases. Recommendations are separate from human decisions.
2. **0:30–1:15 — Evidence.** Open Cases and choose an ESCALATE recommendation. Show the price/trade timing, nine checked evidence links, dealer-to-account path, grounded transcript cue and citations. If audio is available, play the relevant synthetic call. Export evidence JSON to show the portable audit package.
3. **1:15–1:45 — Human control.** Enter a reviewer name and note. Start review, request information, then approve escalation. Show the decision history. Re-run the pipeline; follow progress on Runs and return to the case to show the decision remains intact.
4. **1:45–2:20 — False-positive control.** Open Eval. The six repeated unlinked decoys are REVIEW, while the trade-score baseline falsely escalates them. The planted injection transcript still gets its correct recommendation. Explain that this is a deliberately labelled synthetic benchmark, not measured production accuracy.
5. **2:20–2:45 — Audit.** Open Ledger and verify the chain. With demo controls enabled, tamper with sequence 3 and verify that the exact change is detected. Restore clean ledger only when ready to reset the demonstration; this action removes the demo's decisions.
6. **2:45–3:00 — End-to-end operation.** Show Data validation/export/import and the run history. Mention optional local/hosted model and ASR adapters, offline fallbacks, revision-safe review, atomic publication and the measured detector benchmark.

Before presenting: run `uv run pytest -q` and `uv run pytest -m browser -q`; verify `/api/ready`; keep the application on loopback; test audio volume. Avoid regenerating source data after audio rendering without rerendering. Regeneration and fresh runs do not overwrite old case snapshots, but changed evidence produces a new version.

If a run fails, the previous cases remain available. Inspect the sanitized run error, check Data validation and provider configuration, then resubmit. If no optional provider is configured, keep `DW_LLM=mock` and `DW_ASR=replay` for the reliable offline demonstration.
