# HackIn Drive 2026 submission copy

Use the text below in the Upcoming Engineer project form. It stays within the word limits shown in the form.

## Project title

Dealer Watch

## Problem statement

Compliance teams receive the evidence needed to investigate front-running from separate systems. The fund order is in an order blotter, related trades are in a market feed, account relationships are in KYC records, and the most useful context may be inside recorded dealer calls. Analysts must join those records manually, check whether the timing and profit pattern is meaningful, and build an evidence file that another reviewer can audit. This work is slow, hard to reproduce, and vulnerable to false alarms when a trade pattern has no relationship or communication evidence. Dealer Watch addresses that gap with a repeatable investigation workflow built on synthetic order, trade, account-link, call, and price data.

## Solution overview

Dealer Watch detects same-side trades before a large fund order and opposite-side trades after it using indexed time windows. It then gathers relevant calls, replays or transcribes the recording, extracts grounded leak cues, and connects the dealer to accounts through a relationship graph. A nine-link evidence verifier checks the order, trade timing, profit, repeat pattern, relationship path, call window, cue, and applicable clause. The console presents the case timeline, transcript, audio, graph, evidence links, and a short checked summary. A human reviewer can request information, approve escalation, or dismiss the case. SQLite persistence, revision checks, exports, a background run history, and a hash-chained ledger keep the workflow auditable after restarts and reruns.

## Innovation / USP

Dealer Watch separates evidence discovery from the final decision. Rules perform the risk-sensitive classification, optional language and speech providers only add grounded context, and a reviewer controls escalation. Missing links produce REVIEW instead of an accusation. The system checks every citation and number in a generated explanation against an immutable evidence snapshot, and the ledger makes later edits visible. In the seeded evaluation, all 19 labelled cases matched their expected recommendation, including six unlinked repeated-pattern decoys that a trade-score-only baseline escalated incorrectly.

## Project status

Working prototype / deployed

## Estimated budget

₹50,000

## How the funds will be used

₹12,000 will support the persistent AWS backend, storage, TLS, and backups. ₹3,000 will cover the Vercel frontend, preview deployments, and CI. ₹8,000 will be reserved for optional speech, transcription, and evidence-summary service credits using approved synthetic recordings. ₹7,000 will cover the domain, monitoring, certificate, snapshot, and security operations. ₹10,000 will support demo hardware, connectivity, browser and audio checks, and pitch-video recording. ₹10,000 will cover presentation assets and contingency. The default prototype runs with deterministic mock and replay providers, so the budget supports a reliable demonstration and controlled pilot rather than customer data acquisition.

## Links

- GitHub: https://github.com/PDGamerSG/dealerwatch
- Demo: https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/
- Console: https://dealerwatch-pallab-das-projects-d3f377fd.vercel.app/app
- Backend readiness: https://3.107.131.107/api/ready
- Pitch video: add the YouTube link after recording

## Files to attach

- `PITCH.md` content converted into the project presentation
- Screenshots or diagrams from the landing page and reviewer console
- The recorded 2–3 minute pitch video
