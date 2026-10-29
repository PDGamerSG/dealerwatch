# Declared reusable components

Azentio rule 3: the core must be built during the challenge; existing libraries and your own reusable components are allowed if declared. This rehearsal separates the two.

## `toolkit/` (generic, may be brought to the event and declared)
| File | What it is | Origin |
|---|---|---|
| `toolkit/ledger.py` | Append-only hash-chained SQLite ledger with verify and a tamper demo | Written for this rehearsal; generic technique (hash chains) |
| `toolkit/llm.py` | LLM provider switch (mock, Ollama, OpenAI, Anthropic) with fallback, cache and stats | Written for this rehearsal |
| `toolkit/asr.py` | ASR switch (replay, Sarvam) | Sarvam client adapted from Kyun (hackFront India 2026, MIT, Team Vulcan) |
| `toolkit/grounding.py` | Citation and number checker plus template fallback | Idea from Kyun's answer validator (MIT); rewritten |

Before the event: confirm with HackCulture that a declared generic toolkit is acceptable. If not, rewrite it on the day (about 1.5 hours with this rehearsal as a guide).

## Everything else is the DealerWatch core
`dealerwatch/` (detectors, agents, evidence chain, case builder, pipeline, store, decisions, eval, API, UI) and the synthetic data generator are **rehearsal code**. Rebuild them during the finale. See `DAY_OF_REBUILD.md`.

## Not used
No code from the user's confidential or unfiled patent repositories is included.
