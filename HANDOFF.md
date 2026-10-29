# Handoff: DealerWatch rehearsal (Windows -> MacBook), 29 Oct 2026

Repo: https://github.com/Hydra-Of-Malice/dealerwatch-rehearsal (private). Collaborator invite sent to PDGamerSG (write).
Finale: Azentio.ai Build Labs, 31 Oct 2026, 07:00-23:00, Bengaluru (shortlisted teams only). **This is a rehearsal**: rebuild the core fresh on the day (Azentio rule 3); only `toolkit/` may be brought and declared (see `DECLARED_COMPONENTS.md`, `DAY_OF_REBUILD.md`).

## Done and verified on Windows
- `toolkit/`: hash-chained ledger, LLM switch (mock/ollama/openai/anthropic) with fallback + cache, ASR switch (replay/Sarvam, adapted from Kyun MIT), grounding checker. Ollama `gemma4:e2b` smoke test passed.
- `dealerwatch/`: synthetic universe (seed 7), sandwich detector, link graph, call gathering, grounded leak-cue extraction (rule cues are a floor; LLM can only add grounded cues; injection text cannot change the verdict), 9-link evidence chain, case builder with grounded summary + template fallback, decisions state machine, pipeline, eval harness.
- Rule (revised): REVIEW when order+pre+post+profit ok and (link OR cue OR repeat/large pattern); ESCALATE only with all 9 links.
- API + vanilla-JS UI (queue, timeline, transcript, link graph, evidence chain, decisions, ledger tamper/restore, eval). Screenshot: `docs/screenshot_case.png` (1366x768).
- `pytest -q`: **637 passed**. Eval (mock): all 13 planted cases correct; DealerWatch 13/13 vs rules-only baseline 9/13; case latency p50 15 ms.
- Judge docs: `SUBMISSION.md`, `AI_TOOLS.md`, `DECLARED_COMPONENTS.md`, `DAY_OF_REBUILD.md`, `CONTRACT.md` (design contract). Prep research: `docs/prep/`.

## Not done (in priority order)
1. **Decoy cases** `UNLINKED_PATTERN` (3): unlinked accounts, no calls, sandwich 2 orders with score >= 0.5, expected REVIEW. Add in `dealerwatch/data/synth.py` + `truth.json`; the baseline should then show false escalations (EVAL currently cannot separate the two on ESCALATE because noise produces no background candidates).
2. **Call audio on Mac**: `scripts/make_audio.py` uses Windows SAPI via PowerShell. Add a macOS branch using `say -v Rishi` (dealers) / `say -v Veena` or `Lekha` (others) with `-o tmp.aiff` then `afconvert -f WAVE -d LEI16@16000`, stitch with `wave`, rewrite `start_ms/end_ms` and `audio_file`. Render leak, injection and no-cue calls plus 3 innocent ones.
3. **`tests/test_data_synth.py`**: models validate, determinism, planted counts, TRUE_FR windows + leak call, COINCIDENCE unlinked, injection text present, UNLINKED_PATTERN properties.
4. **Test pass 1 (integration)**: regenerate data, full pytest, eval, run server, click through every case type in a browser, ledger tamper/restore, check JS console.
5. **Test pass 2 (independent)**: a fresh reviewer runs the same from a clean clone on the Mac.
6. **Real LLM path**: `DW_LLM=ollama` end to end; check extraction quality and that summaries pass grounding or fall back cleanly; record latency in EVAL.md.
7. `ARCHITECTURE.md` with a diagram; 3-minute demo video; deck.
8. Fill `EVAL.md` numbers into `SUBMISSION.md`.

## Mac setup
See `README.md`. Paths in `CONTRACT.md` say `.venv/Scripts/python.exe` (Windows); on Mac use `.venv/bin/python`. `data/generated/` and `runtime/` are git-ignored: regenerate with `python -m dealerwatch.data.synth --seed 7 --out data/generated`.

## Kept off GitHub on purpose
The repo-pattern audits (`research/stock-market/D1_*`, `D2_*`) and `STOCK_MARKET_IDEAS.md` mention the user's unfiled patent repositories. They stay on the Windows machine at `D:\bangalore hackathons\06-azentio-ai-build-labs\`. Copy them by hand if needed. No code from patent repos is in this repo.

## Prompt for a Claude session on the Mac
> Continue the DealerWatch rehearsal in this repo. Read HANDOFF.md, CONTRACT.md and README.md first. Do the "Not done" list in order, keep `pytest -q` green after each item, commit after each item, and do not touch `toolkit/` beyond bug fixes. Report EVAL.md numbers at the end.
