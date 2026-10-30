# Dealer Watch pitch pack

This pack gives the team a short video script, a timed presentation, a demo path, and answers to likely judge questions. It matches the live prototype and the HackIn Drive 2026 form copy in `SUBMISSION.md`.

## 2–3 minute video script

**Target length:** 2 minutes 35 seconds
**Presenter:** Aditya Arnav
**Recording:** screen capture with a small presenter window in the opening and closing shots

**0:00–0:15 | The problem**

"A compliance analyst investigating front-running has to join four kinds of evidence: a fund order, trades around that order, account relationships, and recorded dealer calls. Those records usually live in separate systems. Manual joins are slow, difficult to reproduce, and can turn an ordinary repeated trade pattern into a false alarm."

**0:15–0:35 | The product**

"Dealer Watch is a working investigation workflow for that problem. It starts with a large fund order, detects a same-side trade before it and an opposite-side trade after it, then gathers the linked account and the relevant call. The result is a case file a reviewer can inspect in one screen."

**0:35–1:05 | Show the queue and one case**

"This is the queue. Each case has a recommendation, a score, a reviewer state, and a progress history. I will open a planted front-running scenario. The timeline shows the fund order and the matching trades. The relationship graph connects the dealer to the account. The call panel jumps to the utterance that mentions the scrip, side, or size."

**1:05–1:35 | Explain the evidence chain**

"Dealer Watch checks nine links before it recommends escalation: order, pre-trade, post-trade, profit, repeat pattern, relationship path, call window, grounded cue, and rule clause. The summary is accepted only when its citations and numbers exist in the evidence snapshot. If a link is missing, the result is REVIEW. The system does not escalate a person by itself."

**1:35–1:55 | Human review and audit**

"I can request more information, approve escalation, or dismiss the case under my reviewer name. That decision is stored with a revision and an audit event. The ledger is hash chained, so the verify action can identify a changed row. Rerunning the pipeline keeps the human decision and creates a new evidence version."

**1:55–2:15 | Evaluation**

"On the seeded synthetic evaluation, Dealer Watch matched all 19 labelled recommendations: six escalations, ten reviews, and three dismissals. Escalation F1 was 1.000. A trade-score-only baseline escalated six unlinked decoys and scored 0.667 F1. The indexed detector processed 100,000 trades and 1,000 orders in a 412 millisecond median benchmark."

**2:15–2:35 | Close**

"The prototype is deployed with the landing page and console on Vercel and a persistent SQLite backend on AWS. The next step is to connect approved order, KYC, and recording feeds, then run the same evidence and human-review gates on a controlled pilot. Dealer Watch makes the investigation traceable from the first alert to the final decision."

## Shot list

| Time | Screen | Action and narration |
|---|---|---|
| 0:00–0:15 | Landing page hero | Introduce the evidence-joining problem. Keep the page still long enough to read the title. |
| 0:15–0:35 | Landing page workflow section | Scroll through Detect, Gather, Link, Verify, and Review. |
| 0:35–0:50 | `/app` queue | Point out the case totals and run status. |
| 0:50–1:05 | Case detail | Open the planted escalation case and show the timeline. |
| 1:05–1:20 | Evidence chain | Expand the nine-link chain and the clause card. |
| 1:20–1:35 | Call panel | Play or seek the archived audio and highlight the cited utterance. |
| 1:35–1:55 | Decision and ledger tabs | Record a reviewer decision, open the audit view, and show verification. Use a disposable demo runtime if showing tamper and restore. |
| 1:55–2:15 | Evaluation tab | Show the 19-case result and baseline comparison. |
| 2:15–2:35 | Architecture or landing close | Show the Vercel plus AWS deployment split and close on the product name. |

Before recording, seed the runtime, open the queue, keep the case id visible, mute desktop notifications, and confirm that the browser is using the deployed synthetic instance. Record a second take as a backup.

## 10-minute presentation

| Time | Section | Points to cover |
|---|---|---|
| 0:00–0:45 | Problem | Separate order, trade, KYC, and call systems make manual investigation slow and hard to defend. |
| 0:45–1:30 | Product | Dealer Watch creates a case from the same evidence an analyst already needs and keeps the reviewer in control. |
| 1:30–2:30 | Workflow | Detect the sandwich, gather calls, link accounts, check the evidence chain, explain with citations, and record a decision. |
| 2:30–4:30 | Live demo | Open the queue, inspect the planted escalation, play the call, follow the graph, and approve or request information. |
| 4:30–5:30 | Safety and audit | Explain REVIEW for partial evidence, prompt-injection-resistant data handling, revisions, exports, and the hash-chained ledger. |
| 5:30–6:30 | Evaluation | Show 19/19 labelled recommendations, 1.000 escalation F1, the baseline's six false escalations, and the 412 ms detector benchmark. |
| 6:30–7:30 | Architecture | FastAPI, SQLite, NetworkX, a static console, Vercel for the frontend, and one persistent AWS worker for state. |
| 7:30–8:30 | Budget and rollout | Explain the ₹50,000 allocation, synthetic data boundary, and a controlled pilot with approved feeds. |
| 8:30–10:00 | Close | Restate the user, the defensible workflow, the live deployment, and the next integration step. Leave time for the first question. |

## Five-minute Q&A preparation

**Why does a model not make the escalation decision?**

Escalation is a compliance action. Dealer Watch uses deterministic rules for the recommendation and lets a human reviewer make the decision. Optional language and speech providers supply context only. Every summary citation and number is checked against the stored evidence, so an ungrounded response falls back to a deterministic template.

**How do you avoid accusing someone on weak evidence?**

The nine-link chain distinguishes a complete case from a partial one. Missing relationship, call, or cue evidence produces REVIEW. The interface uses prima facie wording and records the reviewer and revision rather than silently changing a case.

**What happens when a transcript contains an instruction?**

Transcript text is untrusted data. It is never executed as a command. The expected injection scenario remains classified by the deterministic evidence pipeline, and the grounding checker accepts only citations and numbers that exist in the evidence snapshot.

**Can the detector handle a full exchange tape?**

The current detector uses indexed time windows and produces the same candidates as the earlier scan with a 15.23x recorded median speedup. A production rollout can move the windowed join to SQL or Spark, keep per-candidate speech and summary calls cached, and partition data by fund or tenant.

**What data would a real pilot need?**

An approved order blotter, trade feed, KYC relationship fields, recording metadata and audio, and the applicable policy clauses. The prototype uses synthetic data so no customer record is needed for the demo.

**Why keep SQLite?**

The hackathon deployment is a single worker with persistent storage. SQLite gives atomic case and audit publication, easy backup, and a small operational surface. A multi-worker production deployment would move the same contracts to a managed relational store and object storage.

**How do you test the product?**

The repository has unit, API, security, persistence, browser, container, landing build, evaluation, and deployment checks. CI runs Python 3.12 and 3.13, Chromium workflows, the Vercel output test, the container smoke test, and the landing typecheck/build.

**What is the budget?**

The requested budget is ₹50,000. It covers durable AWS hosting and TLS, Vercel and CI, optional speech and model credits, monitoring and backups, demo hardware and recording, and presentation assets. The default prototype runs with deterministic mock and replay providers.

## Final demo checklist

- Confirm the Vercel landing page, `/app`, and backend `/api/ready` open.
- Use the seeded synthetic data and confirm the queue has 19 cases.
- Open one escalation, one review, and one dismiss scenario before presenting.
- Keep the reviewer name and decision revision visible.
- Use a disposable demo runtime for any tamper or restore action.
- Do not expose environment files, tokens, local runtime files, or private browser tabs in the recording.
