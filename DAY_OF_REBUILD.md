# Rebuilding DealerWatch on 31 Oct (team of up to 3)

The rehearsal proves the design works. On the day, rebuild the core in a **fresh repository**, using only the declared `toolkit/` (if HackCulture allows it) and this repo as a reference you read, not code you copy.

## First 30 minutes (07:00-07:30)
1. Check in. Read Azentio's problem statements on the HackCulture site and Discord.
2. If a statement is about capital markets, fraud, AML or compliance: map DealerWatch onto it (same skeleton, their data). If open innovation is allowed: pitch DealerWatch as is.
3. If no statement fits: keep the skeleton (detect in code -> gather -> grounded LLM extraction -> verify chain -> human decision -> ledger -> eval) and swap the domain.
4. Ask organisers: Wi-Fi, provided datasets or sandboxes, allowed AI tools and API keys, whether self-generated synthetic data is approved (rule 5), whether a declared toolkit is OK.

## Roles
| Person | Owns |
|---|---|
| A (backend/AI) | models, detector, links, verify, case builder, pipeline |
| B (data/ASR) | synthetic universe, calls, audio, extraction and grounding, eval |
| C (frontend/presenter) | API, UI, demo script, deck, video, SUBMISSION.md |

## Clock
| Time | Goal | Done when |
|---|---|---|
| 07:30-08:30 | Contract + models + data plan written together | Everyone codes against the same models file |
| 08:30-11:30 | Backbone: generator, detector, pipeline (mock LLM), API skeleton, UI queue | A planted TRUE_FR shows up in the UI queue |
| 11:30-14:30 | Links, calls, extraction, evidence chain, case view, decisions | Full chain shows for a TRUE_FR; REVIEW and DISMISS cases correct |
| 14:30-17:00 | Grounded summary, ledger + tamper demo, eval harness, injection case | `pytest -q` green, EVAL.md generated |
| 17:00-19:00 | UI polish, audio seek, link graph, real LLM path on (Ollama or provider), latency numbers | Demo path works twice in a row |
| **19:00** | **Feature freeze** | Only fixes after this |
| 19:00-21:00 | README, SUBMISSION.md, ARCHITECTURE, AI_TOOLS, deck | Repo shareable |
| 21:00-22:00 | Record the 3-minute video, rehearse the pitch 3 times | Backup video saved locally |
| 22:00-23:00 | Submit early (the portal has failed near deadlines before) | Confirmation screenshot |

## Demo script (about 4 minutes)
1. Problem (20 s): Axis MF order, Rs 30.56 crore, months of conduit trades, joined by hand.
2. Queue (15 s): ESCALATE / REVIEW / DISMISS counts from one run.
3. TRUE_FR case (90 s): timeline (buy 41 min before the fund order, sell after), click the leak cue -> audio jumps to the dealer saying it, link graph (dealer -> brother-in-law -> shared phone -> account), 9/9 evidence chain, clause card, grounded summary with citation chips.
4. Hard cases (45 s): LINKED_NO_CALL -> REVIEW (not accused), the injection transcript -> still ESCALATE because code decides.
5. Human + audit (30 s): approve escalation, then Ledger -> Verify -> Tamper -> chain breaks at row N -> Restore.
6. Eval + scale (40 s): DealerWatch vs rules-only (precision, recall, false alarms), latency; how it plugs into an MFund-style blotter and an AMLOCK-style case queue.

## Judge questions to prepare
- Why not let the LLM decide? (Regulator defensibility; it can be prompt-injected; show the injection case.)
- How do you avoid accusing innocent people? (Partial chain -> REVIEW; human decides; "prima facie" wording.)
- How does it scale to a full exchange tape? (Windowed joins in SQL/Spark, per-candidate LLM calls, caching.)
- What about real data? (Order blotter, desk-recording metadata and KYC feeds; no customer data in the demo.)
