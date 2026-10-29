# H. HackCulture (and similar) hackathon winners: what they actually built

Researched 2026-10-29. Scope: projects, not people. Individual names are left out on purpose (the Portkey winners list, for example, names individuals only).
Method: (1) HackCulture public API `https://api.hackculture.io/api/v1/hackathons?limit=50` (62 events) plus `.../hackathon?slug=<slug>` for every slug, filtered on `is_winners_announced`. (2) Winners section of each event page, read in the built-in browser. (3) `gh search repos` for event names. (4) Elastic blog and press coverage. (5) Shallow clones (code not run) in `C:\Users\mradi\AppData\Local\Temp\claude\D--bangalore-hackathons\1718abd7-8dac-4404-8a00-ce11079c7b98\scratchpad\winners\`.
Labels: **CONFIRMED** means a source names the placement. **CLAIMED** means only the builder says so. **HYPOTHESIS** means my inference.

---

## 1. Winners table

HackCulture winner cards show only the team name, theme, prize and member count. They have no project link (`show_winner_submissions=false` on every event except Cine AI Hackfest, and even that page shows no links).

| Event (date) | Place | Team / Project | Repo / post | One-line what |
|---|---|---|---|---|
| Forge the Future 2026 (Elastic+AWS+Sarvam, Mumbai, ~19 Sep 2026) | 1st (Grand) | Frustrated Engineers / **Vigil** | https://github.com/someshwaranM/forge-frustated-engineers ; https://www.elastic.co/blog/mumbai-forge-the-future-hackathon-2026 | Audits mutual-fund RM sales-call audio for SEBI/AMFI violations. Each finding comes with a timestamp, the transcript snippet and the clause it breaks. |
| Forge the Future 2026 | 1st runner-up | Sandboxed / **Eyewitness** | https://github.com/someshwaranM/forge-sandboxed | Incident agent that finds struggling sessions in rrweb replays, confirms "silent" UI failures with a vision model, and files Kibana Cases. |
| Forge the Future 2026 | 2nd runner-up | defcon1 / **MediAudit-X** | https://github.com/someshwaranM/forge-defcon1 ; cleaned public copy https://github.com/devanshupathak9/mediaudit-x | Health-claim intake and adjudication. The verdict is computed deterministically from grounded tool results and written to a hash-chained audit ledger. |
| CIMET AI Hiring Hackathon 2026 (one-day final evaluation, 19 Sep 2026) | CLAIMED win (HackCulture Discord lead). The HackCulture page has no winners. | **RECALL** | https://github.com/pradeepKundekar0101/recall | Outbound AI voice agent that phones a dropped-off energy-comparison lead, finishes the form by voice, saves each field to the CRM, and warm-transfers to a human. |
| Agents That Act (TrueFoundry x Polaris, 1 day, 26 Sep 2026) | Placement UNKNOWN (winners not announced on HackCulture or in search) | **Regress** (same builder as RECALL) | https://github.com/pradeepKundekar0101/regress ; skill: https://github.com/pradeepKundekar0101/regress-runbook | On-call agent for LLM apps. It detects a quality regression statistically, proves the cause by replay, and rolls back only after Slack approval. |
| Sarvam BuildIn' Hours (12h, 9 Aug 2026) | 1 zen; 2 ringzero; 3 snackoverflow; special mention datacode | No repos found | https://hackculture.io/hackathons/sarvam-buildin-hours ; https://digitalterminal.in/tech-companies/zo-house-bengaluru-hosts-sarvam-ai-hackathon | The press ranks the top 3 as: (1) govt-tender discovery and application for MSMEs on Sarvam Vision, (2) Indic-language storytelling for kids, (3) Setu, visual communication for non-speaking people. It does not map these to team names. |
| Sarvam BuildIn' Hours | Placement unknown. HYPOTHESIS: not top-3, since it is not among the 3 named projects. | **Panchayat AI** | https://github.com/pradeepKundekar0101/buildin-hours | Voice agent that phones offline markets to negotiate prices. Each market is a declarative skill file. RECALL reuses this codebase. |
| ZERO TO ONE (Pocket FM, 36h, Jul 2026) | 1 sev poha gang (AI Native Storytelling); 2 alphaq (AI Agents for Media); 3 degenolympians (Creator Superpowers) | No repos found | https://hackculture.io/hackathons/zero-to-one | Projects not described publicly. 6 repos tagged "Pocket FM hackathon" exist on GitHub, but none can be tied to these teams. |
| Bessemer Tech Catalyst (Jul 2026) | 1 alchemists (Aivar track); 2 smart sync (dCortex track); 3 the last minute mavericks (Aivar) | Unverified candidates: https://github.com/rockerspace/Bessemer-Tech-Catalyst-Dcortex , https://github.com/priyam-saha-17/Bessemer-Tech-Catalyst---dCortex---Agentic-CrewOps-Advisor | https://hackculture.io/hackathons/bessemer-tech-catalyst | dCortex repos are "agentic airline CrewOps advisor". Neither repo is proven to be "smart sync". |
| TrackShift Innovation Challenge 2026 | 1 gazoo gateways; 2 synapse; 3 phoenix (AI Motorsport Intelligence) | No repos mapped | https://hackculture.io/hackathons/trackshift-2026 | Not described publicly. |
| FEG Innovation Hackathon 2026 | Per-challenge winners nikhil17, navix, phineas and ferb; runners-up pi nought square, team ezil, team cheetahs | No repos mapped | https://hackculture.io/hackathons/feg-innovation-hackathon-2026-finalists | Digital Entertainment Experience theme. |
| Cine AI Hackfest (Dec 2025) | 1 solo hack (P3); 2 squash (P1); 3 twobrokegirls (P2) | No repos mapped (several "CINE AI HACKFEST" repos exist) | https://hackculture.io/hackathons/cine-ai-hackfest | Film/AI theme. |
| Portkey AI Builders Challenge (Dec 2025) | Winner, runner-up, 2nd runner-up and 4 spot awards (best Portkey use case, best presentation, most innovative approach, best prototype) | Individual entrants, names omitted | https://hackculture.io/hackathons/portkey-ai-builder-challenge | The spot-award categories show what judges reward separately: presentation, prototype, sponsor-tool use. |

No winners were published (on HackCulture or anywhere I found) for: Agents That Act, CIMET, SBI Hackathon @ GFF 2026, Securities Market TechSprint @ GFF, NABARD @ GFF, AI for Good 2.0, Lyzr Agentathon, GitAgent, the Databricks campus editions, or Mphasis Hiring Hackathon. "OSC AI Build" is not in the HackCulture event list. Many SBI GFF repos exist (e.g. `icvasu/sbi-saarthi`, `hamogh-avm/sbi-hackathon-gff-26-team-avaamo`), but none are marked as winners.

Side finding: `azentio-ai-build-labs` is in the same HackCulture API (slug `azentio-ai-build-labs`), so the same Winners card format will apply.

---

## 2. Per-project notes (only projects whose repos I could read)

### 2.1 Vigil: Forge the Future 1st (CONFIRMED by the Elastic blog; the repo/team-name match is strong)
- **Problem:** Mutual-fund distributors manually audit only about 30-35% of RM sales calls. AI risk scores are "black-box" and can't be defended to SEBI auditors. The audit trail is fragmented across spreadsheets.
- **Demo:** Drop call audio into a folder. It is transcribed and diarized (Hindi-English, Sarvam), with LLM role separation (RM vs customer). Deterministic phrase, suitability and disclosure checks produce candidates. An investigator agent verifies each one against indexed SEBI/AMFI chunks. A React dashboard plays the waveform and seeks to the violation timestamp. Case actions are review, escalate and dismiss. Email dossiers go out via Elastic Connectors. Demo video and deck link: https://drive.google.com/drive/folders/1naqyI7tghWqBbJsY8tr_PlczIk0OFNHo
- **Architecture/stack:** FastAPI, Elasticsearch Serverless (hybrid BM25 + dense via Jina embeddings), MySQL plus ES dual-write, AWS Bedrock Claude Sonnet 4 with Gemini fallback, Sarvam STT/translation, React with WaveSurfer.js, Elastic APM.
- **Agent pattern:** Workflow pipeline (ingest, detect, investigate, case) with one investigator agent.
- **Guardrails:** 9-point "Evidence Chain". If any link is missing (timestamp, or a citation that turns out to be hallucinated), the finding is auto-rejected.
- **Evaluation:** `backend/benchmark/benchmark_report.md` scores the full pipeline against a rule-only baseline on 10 labelled calls (precision/recall/F1, category accuracy, latency). The pytest suite is in `backend/tests`.
- **README quality:** Very high. Exec summary, problem with numbers, differentiators, ARCHITECTURE.md, SUBMISSION.md, regulatory corpus doc, phase plan.
- **Deployment:** Not determined from the files I read.
- **Most likely winning feature (HYPOTHESIS):** A regulator-defensible evidence chain (timestamp plus clause plus reasoning) on a real BFSI capital-markets problem. This is the closest analogue to Azentio's domain.

### 2.2 Eyewitness: Forge the Future 1st runner-up (CONFIRMED)
- **Problem:** "The dashboard is green, the customer leaves." Frontend failures that raise no error never show up in logs, metrics or traces.
- **Demo:** A Next.js storefront with 5 injected faults and an rrweb recorder. An operator presses "Run investigation". ES|QL selects sessions with rage/dead clicks, repeat submits or 5xx. Headless Chromium replays them into a clip plus 1 frame per second. A Bedrock vision model reviews the frames, then challenges its own conclusion. Confirmed findings become Kibana Cases with the clip and backend trail. Sarvam adds Hindi/Tamil summaries.
- **Agent pattern:** A "filter cheaply, investigate selectively, challenge before filing" funnel: workflow, one reviewer, a self-critique step.
- **Evaluation:** `eyewitness score --run <id> --truth <traffic-file>` scores precision/recall against the injected ground truth. The README states honestly that unit tests don't prove model precision.
- **Ops polish:** A `doctor` and `setup` CLI, a non-destructive index setup, a demo script, run notes with real limitations, DECK.pdf.
- **Most likely winning feature (HYPOTHESIS):** A visual, verifiable demo (watch the bug happen, then see the case filed) plus measurable scoring against planted faults.

### 2.3 MediAudit-X: Forge the Future 2nd runner-up (CONFIRMED by the blog; the public copy's README says "Winner", which conflicts)
- **Problem:** A claim review takes about 45 minutes. History is unstructured, temporal reasoning is subtle, ICD codes collide (E10.9 vs E11.9), and brand/generic drug names hide interactions.
- **Demo:** The hospital side uploads documents. Each is classified, fields are extracted with confidence and page/excerpt pointers, codes are normalized to ICD-10/CPT, and mismatched dates or bill totals are flagged. The reviewer side runs a streaming adjudication. It returns APPROVE/DENY/REQUEST_INFO with citations, and the reviewer can override.
- **Architecture:** "The LLM chooses which tools to call, the tools produce the facts." Four grounded tools: an ES|QL bi-temporal clinical trajectory, an RRF hybrid policy matcher, an RxNorm/openFDA drug-interaction check, and a SHA-256 hash-chained audit ledger. The verdict is a deterministic function. If the LLM fails, a no-LLM tool sweep still completes the adjudication.
- **Agent pattern:** One tool-calling agent, deterministic decision layer.
- **Evaluation:** `eval/benchmark_results.json` reports precision@1, recall@5 and MRR for retrieval, TP/FP/TN/FN for drug interactions, and p50/p95 latency.
- **Deployment:** docker-compose (backend plus full).
- **Most likely winning feature (HYPOTHESIS):** "Zero-hallucination" by construction (the model never writes the verdict) plus a tamper-evident audit log.

### 2.4 RECALL: CIMET AI Hiring Hackathon (CLAIMED win; repo pushed on the final-evaluation day, 19 Sep 2026)
- **Problem statement (CIMET):** "Teach the phone to listen". Recover a dropped customer journey over a real phone call and know when to hand off to a human. The other PS was a pre-submission QA compliance gate for CRM sales.
- **Demo:** A real outbound Twilio call. The agent picks up the journey, asks only the missing fields, confirms by read-back, and does a per-field `PUT` to a mock CRM that shows live in the operator console's API-log pane. A frustration or escalation detector triggers a warm transfer to a human console with full context.
- **Architecture/stack:** pnpm monorepo. Node 20 TypeScript Express orchestrator and a Next.js 15 console share an SSE event contract. ElevenLabs Scribe STT (Deepgram fallback), ElevenLabs Flash TTS, a pluggable LLM (OpenAI/Anthropic/OpenRouter/Gemini via env switch), Supabase.
- **Agent pattern:** A deterministic dialogue state machine driven by one journey JSON file. The LLM is used only for open-field extraction and sentiment.
- **Guardrails (in the engine, not prompts):** test numbers only, consent gate (throws), no card data by voice (detect plus redact), no advice (off-script route), Do-Not-Call register, opt-out. Normalization (dates, phones, postcodes) is in code. Extraction confidence is multiplied by STT confidence, with read-back as the real gate.
- **Evaluation:** 10 simulated personas with a 9/10 gate, check scripts for dialogue/transport/LLM/voice, and a measured latency table (e.g. 32s to 20s per journey, 13/15 fields hands-free).
- **README quality:** Very high and candid. Status table, known gaps, measured numbers, "manual baseline is zero rather than invented".
- **Most likely winning feature (HYPOTHESIS):** A real phone call working live, with the CRM write visible, plus hard-coded compliance guardrails. It also reused a prior hackathon codebase (Panchayat AI), which is how it got that far in a day.

### 2.5 Regress: Agents That Act (placement UNKNOWN; included because it is the same builder and an agent-safety design)
- **Pattern:** Multi-agent. A TrueForge orchestrator follows a runbook skill and fans out 4 parallel subagents (what changed, segments, customer impact, replay). Replay code runs in a Daytona sandbox.
- **Guardrails:** Detection uses robust z-scores in SQL, not an LLM opinion. Four correlation gates must pass before a cause can be claimed, and `NOT_LOCALIZED` is a valid ending. In "evidence-only narration", any bare number in the report is rejected. There is exactly one production write per incident, it requires approval, and its arguments must equal the frozen proposal. Decisions are locked, and the agent stops on "No". Connectors are allowlisted and read-only.
- **Other:** Mermaid architecture plus an interactive HTML diagram, a pytest suite (state machine, gates, validator), Docker/compose, a Slack and Linear approval flow, a before/after customer-view video.

---

## 3. Minimum winning feature set (MVP) common to winners

Base: the 4 read repos with a confirmed or claimed win (Vigil, Eyewitness, MediAudit-X, RECALL). Regress (unplaced) is noted in brackets.

1. **The LLM only judges; deterministic code decides and normalizes** (rules, SQL, parsers, a computed verdict). **4/4** [+Regress]
2. **Every output is grounded in evidence and cited** (timestamp, clause, page excerpt, replay clip, query id). **4/4** (RECALL's version is read-back plus a logged per-field API call) [+Regress]
3. **Hard guardrails in code that auto-reject ungrounded or unsafe outputs**, not just prompt instructions. **4/4** [+Regress]
4. **Human-in-the-loop as a designed step** (reviewer override, case queue, warm handoff, approval gate). The AI is explicitly advisory. **4/4** [+Regress]
5. **Audit trail of every decision** (case history, per-field event log, hash-chained ledger). **4/4.** Tamper-evident specifically: **1/4** (MediAudit-X).
6. **Quantitative eval against ground truth** (labelled set, personas or injected faults, with precision/recall/F1, MRR, pass gate or latency numbers) checked into the repo. **4/4** [+Regress]
7. **A realistic simulated environment** (fixture calls, a mock CRM endpoint, a storefront with planted faults, a regulatory corpus), so the demo runs end-to-end live. **4/4**
8. **A live operator UI that shows the agent working** (dashboard, streaming verdict, API-log pane, case view). **4/4**
9. **Provider abstraction plus fallback or mock mode** (Bedrock to Gemini, a no-LLM sweep, an env-switched LLM/STT, `MOCK` or `doctor`). **4/4** (Eyewitness: `doctor`, optional Sarvam)
10. **Measured latency and cost awareness** (p50/p95, per-turn budget, APM). **3/4** (Vigil, MediAudit-X, RECALL)
11. **Hybrid retrieval (BM25 plus vector, with RRF or field boosts) over a domain corpus.** **2/4** (Vigil, MediAudit-X; both Elastic-sponsored)
12. **A judge-facing README/SUBMISSION.md** (problem with a number, solution flow, architecture diagram, known gaps, run steps) **4/4**, plus a deck or video **3/4** (Vigil video, Eyewitness DECK.pdf, MediAudit-X pptx). A hosted public URL: **0/4** (everything ran locally or in docker).

Notes for the Azentio pitch (HYPOTHESIS):
- The strongest analogue is Vigil: BFSI capital-markets compliance (SEBI/AMFI) with an evidence chain. It maps directly to Azentio's rubric items "reasoning, security, architecture".
- Forge judges said they rewarded "reliable in production… live data flows… edge cases". Those words point to features 6, 7 and 9.
- The Forge organizers' team template told teams that judges read SUBMISSION.md first (`someshwaranM/forge-defcon1/README.md`). Plan to have a SUBMISSION.md-style doc ready.
- The CIMET-style hiring hackathons put real-integration plus guardrails ahead of breadth. RECALL arrived with a reused, pre-tested codebase.

## Sources
- HackCulture API: https://api.hackculture.io/api/v1/hackathons?limit=50 , https://api.hackculture.io/api/v1/hackathon?slug=cimet-ai-hiring-hackathon-2026
- Winner cards: https://hackculture.io/hackathons/zero-to-one , /sarvam-buildin-hours , /bessemer-tech-catalyst , /trackshift-2026 , /feg-innovation-hackathon-2026-finalists , /cine-ai-hackfest , /portkey-ai-builder-challenge
- https://www.elastic.co/blog/mumbai-forge-the-future-hackathon-2026
- https://digitalterminal.in/tech-companies/zo-house-bengaluru-hosts-sarvam-ai-hackathon
- Repos listed in the table above. All were cloned shallow and none were executed.
