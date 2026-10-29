# G. HackCulture Discord read (29 Oct 2026)

Read-only, via the user's logged-in Discord in the built-in browser. Nothing posted, no reactions. Personal details of members are left out on purpose.

## Channels read
announcement, azentio-tech-catalyst-2026, showcase, general (last ~130 messages), cyberforge-by-mitigata (110 messages), databricks-campus-hackathon, tech4bharat-gavs-hackathon, hackathon-ideas (forum), meetups, hacker-house. Skipped: introduction, buddy, find-a-teammate, memes, support/member-event forums (teammate requests and chatter only).

## Headline
**There are no winner announcements, results, judge feedback or winning-project posts anywhere in the server.** The server is used for announcements, teammate hunting and organiser Q&A. Showcase is mostly spam and self-promotion.

## Azentio channel (#azentio-tech-catalyst-2026)
- 10 messages, 19-26 Oct: teammate requests, one external invite, and four posts of the common crypto-casino scam images ("Activate code for bonus", "Withdrawal successful"). Nothing from organisers, no problem statements, no hints.
- Official announcement (#announcement, 14 Oct, HackCulture program manager): "A Hiring Hackathon by Azentio", INR 3,00,000 prizes, **1-8+ years of professional experience**, **solo or teams of 2-3**, link to the HackCulture page. This settles the team-size conflict: plan for max 3.

## How HackCulture runs hackathons (pattern across events)
From #announcement, #cyberforge, #databricks and the public API (api.hackculture.io/api/v1/hackathon?slug=...):
- Flow: register -> idea submission (deck) -> shortlist by email/site -> one offline build day -> jury round -> final jury demo.
- Problem statements often go live on the website at a fixed time, sometimes late (CyberForge and Databricks participants complained they were not visible on time). Expect the same on 31 Oct: check the site and Discord at 07:00.
- Submission portals have failed near deadlines (CyberForge "not saving at 11:57"). **Submit early.**
- Shortlist communication was patchy (CyberForge participants unsure if they were selected; no rejection mails).
- No travel or accommodation announced for outstation finalists.

### Final-day submission fields HackCulture asks for (from the API, per event)
| Event | Fields |
|---|---|
| Agents That Act (TrueFoundry, Polaris, 1-day Bengaluru) | Describe the project, the problem, **how your AI agent handles it end to end**; **public GitHub repo with working README**; **AI assistants/coding tools used**; **public demo video** |
| Sarvam BuildIn' Hours (12 h) | Description + key features; GitHub; **deployment link**; demo video max 3 min; PPT/PDF |
| Zero to One (Pocket FM, 36 h) | Same as Sarvam, plus a final jury demo |
| AI for Good (Blend360) | Deck; codebase URL; deployed app links. Idea round asked: problem, user engagement, benefits, impact, **obstacles**, **assumptions**, what you build now vs later |
| SBI @ GFF 2026 | Idea, **business model/commercial potential**, stack, **process flow/architecture**, deck, demo video (3 min), GitHub |
| Forge the Future (Elastic+AWS) | Proposed solution, stack, **1-2 page doc with architecture diagram** |
| GitAgent (Lyzr) | Description, public repo, demo video 2-5 min, features used, **run-locally instructions** |
| Azentio (from rules, fields not yet in API) | Repo access, README, architecture overview, models/tools, key prompts/workflows, dependencies, run instructions |

**What this means for us:** have ready before judging: public (or shareable) repo with a README that runs, a deployed or local-run link, a 3-minute demo video, a short PPT with architecture + business value + obstacles/assumptions, and an AI-tools declaration. These are the MVP artefacts HackCulture juries see on every event.

### Judges seen on HackCulture events (roles only)
Forge the Future: Sarvam Head of Strategy, Elastic Head of Field Engineering, AWS Senior Solution Architect (agentic AI), NASSCOM Head of AI. GitAgent: Lyzr AI lead, product, chief architect. Pattern: sponsor's own technical leaders plus cloud architects. Azentio says its "technology leaders" will judge.

## Other HackCulture events seen (for context)
AI for Good 2.0 (Blend360, Hyderabad, Jun), SBI @ GFF (agentic AI for digital banking, Jun), Build with Claude Code x Logitech (Polaris, Jun), Forge the Future (Elastic+AWS, Aug), Zero to One (Pocket FM, Jul), Sarvam BuildIn' Hours (12 h, Aug), Agents That Act (TrueFoundry, Polaris, 26 Sep), CyberForge (Mitigata, 31 Oct-1 Nov), Tech4Bharat (GAVS), Global AI Hackathon (Geek Room, Bifrost).
Only Zero to One and Sarvam BuildIn' Hours have `is_winners_announced: true` in the API, but winner submissions are hidden (`show_winner_submissions: false`).

## Leads for winners (to follow outside Discord)
- One CyberForge participant says they "won the Cimet Hiring Hackathon last month" and posted their GitHub profile. Cimet is a hiring hackathon like Azentio's; their public repo for it is worth reading (project only).
- Forge the Future India 2026 winners are already in C_winning_patterns.md (Vigil, MediAudit-X, Eyewitness).
