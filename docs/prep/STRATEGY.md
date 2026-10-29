# Azentio.ai Build Labs: strategy (finale 31 Oct 2026, Bengaluru, 07:00-23:00)

Built from research/A_event_scrape.md, B_azentio_company.md, C_winning_patterns.md. FACT = sourced there. HYPOTHESIS = inference.

## 1. Who is behind it and why (short)
- FACT: "Azentio.ai" is the event brand. The company is **Azentio Software** (azentio.com): Singapore HQ, Apax-owned since Dec 2020, 650+ clients, 1,900+ staff, strong in Middle East, Africa, Asia. azentio.ai itself is only a parked GoDaddy page.
- FACT products: iMAL (Islamic core banking), Lending / Loan Origination, AMLOCK (KYC, AML, sanctions, fraud, case management), Claim Automation (insurance), MFund (capital markets), Orion ERP (incl. UAE e-invoicing with "embedded AI", July 2026).
- FACT motive: it is a **hiring hackathon**. Registration form asked for the role applied for (Forward Deployed AI Engineer, Senior, Lead, Technical Architect - AI & Innovation) and BFSI/ERP background. Prize INR 3L + fast-track interviews. Judges are Azentio technology leaders.
- FACT: no problem statements, themes or venue published yet. Themes stay "REVEALING SOON". The scorecard: problem understanding, working functionality, intelligence/reasoning, architecture, security, usability, originality, scalability. Each member must explain what they built.

## 2. Likely problem statements (all HYPOTHESIS), ranked
| Rank | Problem area | Why likely | Fit with winners |
|---|---|---|---|
| 1 | AML/KYC alert triage + investigation copilot | AMLOCK is their flagship and most-awarded product | Resistant AI (relationship analysis), Vigil (cited clause) |
| 2 | Document intelligence: KYC / onboarding / trade docs | Named theme "document intelligence" | MediAudit-X (docs to structured case, cited rules) |
| 3 | Loan origination and credit decisioning agent | "Decisioning as a service" is a product line | Reg Central, NovaMind (auditable decisions) |
| 4 | Insurance claims automation (FNOL to settlement) | Claim Automation product, Celent recognition | Felix (Duck Creek), UiPath ClaimGuardian |
| 5 | ERP finance ops: invoice capture, e-invoice validation, NL ERP queries | July 2026 AI e-invoicing launch | - |
| 6-8 | Customer assistant, regulatory RAG, delivery productivity | Named in the event text but generic | - |

## 3. Which one to choose when statements drop
You cannot choose before 31 Oct 07:00. Decide in the first 30 minutes with this scorecard (score 1-5, pick highest total):
1. **Fit to the 8 judging criteria** (can a working end-to-end slice show reasoning, security and scale?)
2. **Data provided** (approved synthetic data or sandbox exists? If not, can you generate it in 30 min with Faker?)
3. **Team skill match** (who knows the domain vocabulary?)
4. **Demo wow in 4 minutes** (visible evidence, tricky case, audit trail)

**Default pick if several are offered: AML/KYC alert triage + investigation copilot with document intelligence for the KYC pack.** Reasons: flagship product (so judges care), synthetic data is easy to make, graph and audit trail are visible in a demo, it matches the most winning patterns (cited evidence, relationship analysis, human-in-the-loop). Tie-breaker order: AML > claims > loan decisioning > ERP.

If the statement is none of these, reuse the same skeleton (section 4).

## 4. What to build (a reusable skeleton that fits any of ranks 1-5)
One vertical slice: **input, extraction, reasoning, decision, human review, audit record.**
- Ingest a document or alert (parse/OCR) then mask PII.
- LLM extracts to a JSON schema (pydantic validation).
- **Deterministic rules decide**; the LLM extracts and explains. Never let the LLM make the final call.
- Retrieval over synthetic policy/regulation text; every output cites the clause, rule fired, and source span.
- Confidence gate: auto-recommend only above threshold, else route to a human queue; analyst override is logged.
- Append-only, hash-chained audit log shown in the UI, with exportable case file.
- Small labelled test set (30-50 synthetic cases) with an accuracy/abstain table in the UI, plus one red-team case (prompt injection inside a document).
- Stack: Python + FastAPI + pydantic + SQLite; Streamlit (or Next.js if a frontend person is in the team); networkx for the AML relationship graph; pytest for the eval set.
- Fallback for bad venue internet: local model via Ollama, response cache for scripted demo cases, deps and weights pre-downloaded, phone hotspot, recorded backup demo.

### Rule check (important)
- Core solution must be **built during the challenge**. Prepare only generic reusable pieces (audit-log helper, provider switch, PII masker, test harness) and **declare them** in the README. Do not walk in with a pre-built solution.
- No customer or production data; use only provided or approved datasets/APIs/sandboxes. Label all data synthetic. No Azentio/customer secrets into public AI tools.
- Disclose every AI tool/model used (including coding assistants). Everyone must be able to explain their own part.

## 5. Before 31 Oct
- [ ] Check email / HackCulture for the **shortlist notice**. Registration closed 25 Oct and only shortlisted teams attend. If none: email manvendra@hackculture.in and support@hackculture.in today.
- [ ] Join Discord: https://discord.gg/M58Ygk534 (problem statements, venue, rules will likely appear here).
- [ ] Ask organisers: venue, Wi-Fi, whether API keys/credits are provided, which AI tools are allowed, team size (header says 2-4, FAQ says up to 3). Venue is unpublished; HYPOTHESIS: Azentio Bengaluru office, 5th Floor, Wing B, Electra Block, Exora Business Park, Kadubeesanahalli, ORR, 560103. Confirm.
- [ ] Check-in is required on the day; arrive by 07:00.
- [ ] Assign roles: presenter/domain lead, backend+AI, frontend/demo, eval+security+docs. Presenter learns the vocabulary (KYC, CDD/EDD, sanctions screening, SAR, false positives, LOS, FNOL, e-invoicing).
- [ ] Pre-download: Python deps, a small local model (Ollama), embedding model, Docker images; set up two LLM providers; charge laptops, bring chargers and hotspot.
- [ ] Pre-write: README template with an AI-tools declaration, an architecture diagram template, and a 4-minute demo script skeleton.

## 6. Finale-day clock (16 hours; adjust to real schedule)
| Time | Do |
|---|---|
| 07:00-08:30 | Check in. Read problem statements. Score them (section 3). Pick one. Write one sentence: persona + pain + KPI. Ask Azentio staff which workflow hurts most. |
| 08:30-10:00 | Plan: data schema, rules list, screens (max 5), who builds what. Generate synthetic data. |
| 10:00-14:00 | Backbone running end to end with the ugliest UI. Deploy locally. |
| 14:00-17:00 | Rules, retrieval with cited clauses, confidence gate, human queue, audit log. |
| 17:00-19:00 | UI polish for the demo path, graph/evidence drill-down, security slide items (PII masking, roles, injection check). |
| 19:00 | **Feature freeze** (2-3 h before judging). Only fixes after this. |
| 19:00-21:00 | Eval table, red-team case, README, architecture diagram, AI-tool declaration. |
| 21:00-22:30 | Record backup demo video. Rehearse pitch 3 times. Pre-seed the DB. |
| 22:30-23:00 | Final check: can we demo right now? Repo access ready. |
Check "can we demo right now?" every two hours. Times depend on when judging actually happens; confirm the schedule on arrival.

## 7. Demo script (about 4-5 minutes)
1. Problem, persona, KPI (20 s).
2. Happy path live (90 s).
3. Tricky case where the system abstains or flags and routes to a human (45 s).
4. Evidence drill-down and audit trail (30 s).
5. Eval numbers and architecture (45 s).
6. Scale and how it plugs into an existing platform such as AMLOCK or Claim Automation (30 s).
Prepare answers for: scalability, security, cost per case, edge cases, why not pure LLM.

## 8. Biggest risks
- Not shortlisted, or problem statements fit none of the above (use the skeleton anyway).
- Free-form autonomous agents on stage: avoid. Use scripted deterministic paths plus one unseen case from the test set.
- Claiming accuracy without the eval table, or claiming "compliant with X" (say "maps to clause X").
- Spending over 20% of time on UI before the decision gate and audit log work.
- Unclear rule on reusable code: ask organisers and declare everything.

## 9. Gaps in the research
- No problem statements, venue, mentors or datasets were published.
- No Azentio AI product or LLM/cloud partner was found; the only AI announcement is the July 2026 UAE e-invoicing launch.
- Most "why it won" reasons for past winners are inference; judge quotes exist only for Forge the Future (guardrails, edge cases) and GitLab ("feels like a product").
- The Field CTO podcast and the Java/Struts job post were read only via search summaries.
