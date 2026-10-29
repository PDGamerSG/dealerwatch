# C. Winning patterns for enterprise / BFSI AI hackathons (Azentio.ai Build Labs prep)

Research date: 2026-10-29. Convention: **FACT** = stated in the cited source. **HYPOTHESIS** = my inference, not stated by any source. Nothing here is fabricated; where a source gave no reason for a win, that is said.

## 0. Coverage gaps (be honest)
- **Lyzr Agentathon (Bengaluru, Rs 2 lakh, solo/2-person, must use Lyzr Architect):** only event description found, no winners published in anything I could reach. https://www.startupgrantsindia.com/events/lyzr-agentathon-the-2-lakh-vibe-coding-challenge
- **GitAgent, OSC AI Build 1.0:** no winner lists found (OSC AI Build 1.0 listing only: https://internshala.com/competitions/osc-ai-build-1-0/).
- **HackCulture Databricks Campus Hackathon (Bengaluru, Sept 2026):** series and finale at PES University documented; no winners found. https://luma.com/r6d8xrij
- Most sources publish **no formal scoring rubric or judge reasoning**. "Why it won" below is mostly HYPOTHESIS unless a judge quote is cited.
- Devpost/Devfolio/Unstop searches returned few KYC/AML/loan-underwriting winners with write-ups. No confirmed winning loan-underwriting hackathon project found (only vendor awards / unconfirmed entries).

## 1. Table of concrete past winners

| # | Event (org) | Winner / project | What it did | Source | Pattern that (probably) made it win |
|---|---|---|---|---|---|
| 1 | Forge the Future India 2026 (Elastic + AWS + Nasscom + Sarvam; **HackCulture is a partner**; 20 teams, 2-day Bengaluru finale, 8,000 registrations) | **Vigil** (Team Frustrated Engineers), Grand Winner | Audits sales-call audio for SEBI/AMFI violations (e.g. unverified return promises); multilingual transcription, hybrid search over regulations, flags exact timestamp + matching clause | https://www.elastic.co/blog/mumbai-forge-the-future-hackathon-2026 | **FACT:** BFSI-regulatory problem, evidence-linked output (timestamp + clause). HYPOTHESIS: verifiable citation to the rule is what let compliance reviewers trust it; India-specific regulation (SEBI/AMFI) = strong problem understanding |
| 2 | Same | **MediAudit-X** (Team defcon1), 2nd runner-up | Hospital uploads docs -> structured claim; reviewer recommendations with **cited policy rules**, treatment history, drug-safety checks; approved claims in **tamper-proof audit log** | same URL | **FACT:** claims doc intelligence + cited rules + audit log placed top 3. Closest analogue to a BFSI/insurance Azentio problem |
| 3 | Same | **Eyewitness** (Team Sandboxed), 1st runner-up | Detects silent frontend failures, replays, confirms the failure, files a case with clip + backend trail; Sarvam AI to Hindi/Tamil summaries | same URL | **FACT:** closed-loop (detect -> verify -> file case). HYPOTHESIS: "confirm before acting" step = reasoning + trust |
| 4 | Same (judge observations) | (cross-team) | Teams used **ES\|QL as deterministic guardrails** to stop AI taking unauthorized actions; strong context engineering; judges prioritised robust, scalable systems handling live data flows, complex queries, edge cases ("engineered for real-world reliability") | same URL | **FACT** (judge-side statement): deterministic guardrails + edge-case handling are explicitly noticed |
| 5 | Elastic Forge the Future Singapore 2025/26 (4-hour build, 21 teams) | **Buckle Up 4 AI** (Standard Chartered), Financial Insights Accelerator | Elasticsearch RAG over earnings-call transcripts/public data with multiple LLMs; answered finance queries in demo | https://www.elastic.co/blog/takeaways-forge-the-future-hackathon | **FACT:** article credits "a clear idea, solid framework and flawless execution"; stack matched to problem. Same team later a finalist with "ElasticClaw: explainable decisions at scale" (https://www.elastic.co/blog/singapore-forge-the-future-hackathon-2026-recap) |
| 6 | Innovate.DTCC AI Hackathon 2025 (5 days virtual, 35 teams) | **CIBC "Reg Central"** - Gold ($100K): Automated Regulatory Change Management | Regulatory change automation | https://www.finos.org/blog/ai-strategic-initiative-series-innovate-dtcc-ai-hackathon | **FACT (rubric):** judged on technical innovation/originality, impact on financial markets, presentation/clarity, industry collaboration & scalability; 15-min pitch. HYPOTHESIS: reg-compliance automation maps directly to the "impact" criterion |
| 7 | Same | **Cipher Sentinel** (Duke master's students) - Best Academic: AI Anti-Money-Laundering for digital wallets | Monitors wallets and flags suspicious activity in real time; kept open source via FINOS | https://masters.pratt.duke.edu/news/duke-engineering-students-awarded-for-ai-powered-anti-money-laundering ; https://www.dtcc.com/dtcc-connection/articles/2025/april/02/dtcc-announces-winners-from-first-ai-powered-hackathon (via search snippet) | **FACT:** AML + timely regulatory hook (article ties it to upcoming US AML requirements). Architecture/why-won not published |
| 8 | Innovate.DTCC 2026 | **NovaMind** (Deutsche Bank) - Silver $75K: multi-agent post-trade exception handling "auditable and economical at enterprise scale"; Gold: Snowflake+DTCC agentic threat-hunting; Bronze OpsFlow (FINOS CALM compliance) | | https://www.dtcc.com/insights/2026/innovate.dtcc-2026-industrypowered-ai-hackathon-winners | **FACT:** page stresses business-aligned, scalable-beyond-PoC solutions. HYPOTHESIS: auditability + cost story + alignment to a recognised standard is a recurring winning narrative |
| 9 | Vista Agentic AI Hackathon 2025 (Duck Creek, 24 h, insurance core systems) | **Felix** (team Featherweights), Best AI Agent | Multi-modal, multi-agent First Notice of Loss: ingests text/images/video, triage, fraud flags, claim assignment | https://www.duckcreek.com/resource/blog/duck-creek-technologies-wins-first-prize-for-best-agent-at-the-2025-vista-agentic-ai-hackathon/ | **FACT:** built in ~1 day, claims-intake workflow, mixed team incl. a student. Reasons for win not stated. HYPOTHESIS: multi-modal input = visible "wow" in a demo; one end-to-end business workflow |
| 10 | UiPath AgentHack 2025 (global; criteria: innovation, business impact, technical feasibility, completeness, presentation, community vote) | **ClaimGuardian 360** (2nd, Enterprise Agents); **Smart Health Claim Assistant** (3rd) | Claims fraud detection/validation/resolution guidance; medical claim verification & reconciliation | https://www.uipath.com/community-blog/community-news/uipath-community-annual-global-hackathon-2025 | **FACT:** two of three enterprise podium spots were insurance-claims agents. Shows claims is a high-hit domain |
| 11 | ACAMS AML conference hackathon (PwC-sponsored; 5 days; 10 teams; synthetic data: 1.1M customer records, ~200K cash txns, crypto, sanctions lists) | **Resistant AI + ComplyAdvantage** - "Digital Crime Fighter of the Year" (twice) | Ensemble anomaly detection on synthetic data found identity-obscuring txns, relocated shells, intermediaries | https://financialit.net/news/artificial-intelligence/resistant-ai-awarded-digital-crime-fighter-year-second-time-hackathon | **FACT:** CEO says key was analysing hidden **relationships** between identities and transactions; judges credited data-driven approach. Graph/link analysis on synthetic data fits "no customer data" rule |
| 12 | GitLab AI Hackathon 2026 (~7,000 devs, 600+ agents; criteria: technical work, design, impact, idea) | **LORE** (Grand Prize, 8 agents + router + loop prevention + dashboard, **43 tests**); **DocSync** (Anthropic runner-up: PR when confident, issue for a human otherwise); **Time-Traveler** (real PostgreSQL data, real GCP deploy) | | https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/ | **FACT:** judge quote "This feels like a product, not a hackathon project"; tests, real deployments, human-in-the-loop confidence gating, polished UX all rewarded |
| 13 (bonus) | Hedera Hello Future Apex | **Lamina** (3rd DeFi): agent runs tokenised-bond lifecycle incl. KYC/OFAC screening; **Golden Needle** (2nd): regulatory (UK Building Safety Act) with AI agents + tamper-proof audit trail | | https://hedera.com/blog/these-are-the-winners-of-the-hello-future-apex-hackathon.md | **FACT:** source says "why won" not published (inference only). HYPOTHESIS: named regulation + audit trail again |

Related, non-hackathon signal: RapidData won an "AI Underwriting Implementation of the Year" award; reported (vendor-published) that judges highlighted the **regulator-facing explainability layer** (https://rapiddata.com/insights/news/ai-underwriting-implementation-of-the-year.html). Treat as vendor claim.

## 2. General evidence on what wins (quality-graded)
All below are **blog / practitioner advice, no measured data** unless noted.
- Winners explainable in one sentence; demo shows it working; AI is clearly necessary; execution visible; audience obvious (qualitative read of OpenAI Open Model Hackathon winners; author says no stats). https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla
- Working live demo weighted most; pick the single thing the demo must show; <=5 screens; feature freeze late; record backup video; practice pitch ~5x; prep 3 likely judge questions; ~160 s pitch: problem 10 s, solution 10 s, demo 90 s, why-it-works 30 s, scale 20 s. Author states 80/20 split is an estimate, not measured. https://blogs.reskilll.com/how-to-win-hackathon-2026-complete-playbook/
- Read rubric first; mock/cache external calls so demo reaches key moment; judges ask scalability/security/cost/edge cases; state tradeoffs. https://blogs.reskilll.com/hackathon-demo-presentation-tips-pitch-3-minutes-win-2026/ , https://www.hackerearth.com/blog/10-tips-win-hackathon
- Recurring explicit judge-side signals in sources above: cited evidence, tamper-proof audit log, deterministic guardrails (ES|QL), confidence gating to human, tests, real data/deployment, regulatory-clause mapping.

## 3. Winning playbook for a 1-day BFSI-flavoured AI build (HYPOTHESIS unless tagged)
Mapped to Azentio criteria (problem understanding, working functionality, intelligence/reasoning, architecture, security, usability, originality, scalability).

1. **Hour 0-1: restate the problem as one sentence + one persona + one KPI** (e.g. "AML analyst clears alerts 5x faster with cited reasoning"). Ask mentors/Azentio staff which workflow hurts; real-problem understanding is the first criterion. (Pattern: Vigil/MediAudit-X chose a concrete regulator-facing pain.)
2. **One vertical slice, end to end**, not breadth: input -> extraction -> reasoning -> decision/recommendation -> human review -> audit record. <=5 screens. (Felix did FNOL in ~1 day; Reskilll scoping advice.)
3. **Make the decision layer deterministic + LLM-assisted.** LLM extracts/explains; rules/thresholds/scoring (Python/SQL) decide; policy limits enforced in code. Directly echoes the Forge the Future judge observation on deterministic guardrails (FACT) and covers "intelligence" + "security".
4. **Every output carries evidence**: source document span/page, policy clause ID, rule that fired, confidence. (Vigil timestamp+clause, MediAudit-X cited rules - FACT.)
5. **Human-in-the-loop with confidence gating**: auto-clear only above threshold, else route to analyst (DocSync pattern - FACT). Show an analyst override that is logged.
6. **Append-only, hash-chained audit log** visible in the UI (MediAudit-X "tamper-proof audit log" - FACT; hash chain in SQLite is cheap). Export a case file PDF/JSON.
7. **Security slide that is real**: synthetic data only (their rule), PII masking before LLM call, role-based access (analyst/approver/auditor), no secrets in repo, prompt-injection check on uploaded docs, model/tool declaration page (they require AI-tool declaration).
8. **Evaluation + guardrail story in the demo**: a small labelled synthetic test set (e.g. 30-50 cases), show precision/recall or accuracy, a red-team case (injection in a document, conflicting data), and an "abstain" case. LORE won partly on 43 tests (FACT); eval harness is HYPOTHESIS-level differentiator since most teams skip it.
9. **Originality via one twist**, not a new domain: e.g. entity-relationship/graph view for AML (Resistant AI's hidden-relationship insight - FACT), multilingual doc ingestion (Sarvam use in Forge - FACT), or cost/latency dashboard (NovaMind "economical at scale").
10. **Scalability slide, not scalability code**: stateless API, queue for async doc processing, pluggable model provider, tenant-aware schema, what would change at 10M txns/day. Judges ask this (blogs, DTCC rubric "scalability").
11. **Plan the clock** (one day): ~0-1 plan; 1-6 backbone running + deployed locally; 6-9 vertical slice with real flow; feature freeze ~2-3 h before demo; final block for eval numbers, backup video, pitch rehearsal x3. Check "can we demo right now?" every 2 h.
12. **Team roles (2-4):** presenter/domain, backend+AI, frontend/demo, eval+security+docs. Presenter owns Azentio-domain vocabulary (ERP, AML, KYC, loan origination, general ledger).
13. **Demo script (~4-5 min):** problem (20 s) -> happy path live (90 s) -> tricky case where system abstains/flags (45 s) -> audit trail + evidence drill-down (30 s) -> eval numbers + architecture (45 s) -> scale/next steps (30 s). Keep recorded backup video and pre-seeded cases; pre-cache LLM responses for the scripted cases.
14. **Pitch to the sponsor's product thinking:** Azentio sells AML, core banking, ERP, insurance products; position as a module/assistant that plugs into existing case management (HYPOTHESIS: judges from a vendor reward "could ship inside our platform", cf. judge quote "feels like a product" at GitLab).

## 4. Recommended reference architecture (BFSI doc-to-decision agent)

```
[Upload / synthetic feed]
      |
[Ingestion svc] --OCR/parse (pdfplumber / Tesseract / vision LLM)--> [PII masker]
      |
[Extraction (LLM, JSON-schema constrained)] --> [Validation: pydantic + rules]
      |
[Retrieval: policy / regulation corpus (hybrid BM25 + embeddings)]  <-- RAG over synthetic policies, KYC/AML rules, product terms
      |
[Reasoning orchestrator (small state machine, 3-5 tools, NOT free-form agents)]
   tools: rules_engine, risk_score, entity_graph, sanctions_lookup (mock list), calculator
      |
[Decision gate: deterministic policy + confidence threshold]
   high conf -> auto-recommend ; low conf / high risk -> human queue
      |
[Case UI (analyst/approver/auditor RBAC)] <-> [Append-only hash-chained audit log]
      |
[Eval harness + dashboard: accuracy, abstain rate, latency, cost/case]
```

**Stack (HYPOTHESIS: chosen for one-day speed, not from winner data):**
- Backend: Python 3.11 + FastAPI + pydantic (schema-constrained LLM output) ; SQLite (or Postgres via docker) ; hash-chained audit table.
- Orchestration: plain Python state machine or LangGraph only if the team already knows it (less magic = fewer demo failures).
- LLM: primary hosted API (declare it) via a thin provider-abstraction layer; temperature 0; JSON mode.
- Retrieval: SQLite FTS5/BM25 + small local embedding model (e.g. bge-small / all-MiniLM via sentence-transformers) in FAISS or Chroma; hybrid like Vigil used hybrid search (FACT for Vigil; tool choice mine).
- Graph view: networkx + pyvis/cytoscape.js for AML relationship demo.
- Frontend: Streamlit (fastest) or Next.js + shadcn if a frontend person is present; evidence drill-down panel is non-negotiable.
- Eval: pytest + a JSONL golden set of 30-50 synthetic cases; print a metrics table into the UI.
- Synthetic data: Faker + hand-written edge cases (structuring, name-match near misses, mismatched docs, prompt-injection PDF).

**Fallback if internet/API fails on site:**
1. Local model via Ollama or llama.cpp (e.g. Qwen2.5 7B / Llama 3.1 8B instruct, quantised) pre-downloaded on all laptops; the provider abstraction switches with an env var. Test the local path before the event; expect lower extraction quality, so keep rule-based extraction (regex/templates) for the demo documents.
2. **Response cache / record-replay** of every LLM call keyed by prompt hash, pre-populated for all scripted demo cases (FACT-based advice: mock/cache external calls, reskilll tips).
3. Local embeddings + local vector store; no network at runtime. Pre-pull all pip/npm deps, Docker images, and model weights to a USB drive and each laptop.
4. Mobile hotspot as network backup; pre-created API keys with credit; two providers configured.
5. Recorded 3-min backup demo video + screenshots in the slide deck; run the demo from a pre-seeded DB.
6. Ask organisers in advance about Wi-Fi, allowed AI tools, whether API keys/credits are supplied (rules require declaring AI tools).

## 5. Quick risk checklist (HYPOTHESIS)
- Do not demo free-form autonomous agents on stage; scripted deterministic paths + one live "unseen case" run from the golden set.
- Do not use real customer data or real names; label all data synthetic.
- Do not claim accuracy without the eval table; do not claim "compliant" with a regulation, say "maps to clause X".
- Do not spend >20% of time on UI polish before the decision gate + audit log work.
- Declare every AI tool (coding assistants, models, embeddings) on the submission.
