# Azentio.ai Build Labs - Event Scrape (A)

Scraped 2026-10-29 via own browser tab. Sources:
- PAGE = https://hackculture.io/hackathons/azentio-ai-build-labs (alias https://hackculture.io/hackathon/azentio-ai-build-labs works too)
- API = https://api.hackculture.io/api/v1/hackathon?slug=azentio-ai-build-labs (HTTP 200, public JSON, the page's own data source; no auth). Event _id `6ac35a2947aef38902702d3f`. API `updated_at`: 2026-10-27T20:00:43Z. Page og:updated_time: 2026-10-28T19:05:46Z.

## BOTTOM LINE
- NO problem statements, NO themes, NO venue address, NO mentors/judges, NO datasets/resources are published anywhere I could reach. Verified empty in the API: `themes: null`, `judges: []`, `mentors: []`, `resources: null`, `events: []`, `location.address: null`, `location.coordinates: null`, `location.place_id: null`.
- Venue = only "Bengaluru" (city only).
- Themes tab says literally: "REVEALING SOON - Problem statements and theme tracks are currently being finalized. Stay tuned."
- The only communication channels with extra info: Discord invite and WhatsApp group (links below; I did NOT join), plus a Google Form announcement (mandatory additional details form, deadline passed).
- No web posts found by web search (LinkedIn/Instagram/X/Luma/Unstop/Devfolio): nothing on this event.

---
## VERIFIED (source: PAGE / API above)

### Header
- Title: Azentio.ai Build Labs. Tagline: "Build Intelligence. Create Impact"
- By Azentio.ai (organizer). HackCulture = "Implementation Partner".
- Dates: Oct 8, 2026 - Oct 31, 2026 (API: start 2026-10-08T14:30:00Z = 8 Oct 8:00 PM IST; end 2026-10-31T17:30:00Z = 31 Oct 11:00 PM IST)
- Team: 2-4 members (API min_team_size 2, max_team_size 4)
- Location: Bengaluru. Mode: "Offline Hackathon" (API mode `offline`)
- Status: "Registration Closed" (API `is_registration_open: false`)
- Stats on page: 1,731 registrations (total_participants 1731), 17,341 impressions (total_views 17342)
- Tag: is_featured=true. industry: technology. visibility public. status published, is_completed false, is_winners_announced null.
- Feature flags: team_directory true, ai_judging false (resolved_flags: hackathons, challenges, multi_phase, exports, assessments, team_directory = true; ai_judging = false)

### Overview (verbatim)
azentio.ai in partnership with HackCulture brings together ambitious builders, problem-solvers, AI enthusiasts and AI amplifiers to turn bold ideas into real, working solutions.

This hackathon is designed to go beyond experimentation. Participants will identify meaningful problems, apply AI thoughtfully, and build solutions that demonstrate real-world value. Whether it is intelligent automation, AI agents, decisioning, document intelligence, customer experiences or an entirely new idea, the focus is simple: build something that matters.

The hackathon creates a space to think boldly, build rapidly, experiment freely and demonstrate what AI can make possible.

THE CHALLENGE
Build a working AI-powered solution for a real-world problem statement from Azentio.ai. Participants will be evaluated on the quality of their solution, technical implementation, innovation, business relevance and their ability to demonstrate a functional build.

HACKATHON HIGHLIGHTS
- ₹3,00,000 total prize pool
- Solve a real Azentio problem statement
- Build and demonstrate a working prototype
- Get evaluated by Azentio's technology leaders
- Mentorship and industry exposure
- Fast-track interview opportunities for top performers

WHY PARTICIPATE?
- Turn an idea into a working AI solution
- Solve meaningful enterprise problems
- Showcase your technical and problem-solving capabilities
- Compete for a ₹3,00,000 prize pool
- Explore direct hiring opportunities with azentio.ai
- Gain mentorship, recognition and industry exposure

Build something that matters. Show what AI can make possible.

(Overview markdown also embeds an image captioned alt "Azentio Tech Catalyst 2026" - leftover template alt text, no content.)

### Schedule (page + API phases)
1. Registration (type registration, online, "Approval required", elimination round): 08 Oct 2026 08:00 PM - 25 Oct 2026 11:59 PM (API end 2026-10-25T18:29:00Z = 25 Oct 11:59 PM IST). "Submit your resume and registration details to apply for the hackathon. Applications will be carefully reviewed based on your background and responses, with selected participants moving forward to the next stage."
2. Team Formation (online): 08 Oct 2026 08:00 PM - 26 Oct 2026 11:59 PM. "Shortlisted participants will move to the team formation stage, where they can form teams and collaborate with other selected participants ahead of the hackathon."
3. Final Hackathon Day (type submission, OFFLINE, check_in_required: true, elimination round, evaluator: organizer, allow_multiple_submissions false): 31 Oct 2026 07:00 AM - 11:00 PM IST (API 2026-10-31T01:30:00Z to 17:30:00Z). "Shortlisted teams will advance to the Grand Finale in Bengaluru, where they will build, refine and present their solutions to Azentio.ai's technology leaders."
   - Note: phase has `evaluation_metrics: null`, `submission_questions: null` (no published submission form/rubric weights).
   - Note: check-in is required on the day.

### Themes
"REVEALING SOON - Problem statements and theme tracks are currently being finalized. Stay tuned." (API themes: null)

### Prizes (verbatim)
"Compete for a ₹3L prize pool. Get a participation certificate on completion."
- Winner: ₹1,50,000 cash, 1 winner - Awarded to the top-performing team for outstanding innovation and execution.
- Runner-up: ₹90,000 cash, 1 winner - Awarded to the team with the second-best overall performance and strong execution.
- Second Runner-up: ₹60,000 cash, 1 winner - Awarded to the team demonstrating strong technical execution and impact.
- Job Opportunities: "Direct hiring opportunities with azentio.ai and mentorship from industry leaders."

### Partners (verbatim)
- Azentio (Organizer) - https://www.azentio.com/ : "Azentio.ai is a global enterprise software company building solutions for banking, insurance, ERP and AML. Its platforms help businesses across the Middle East, Africa and Asia manage critical operations with modern technology. Azentio.ai focuses on delivering industry-specific software for BFSI and enterprise customers, helping organisations improve efficiency, manage risk and drive digital transformation."
- HackCulture (Implementation Partner) - https://hackculture.io/ : "HackCulture is a global innovation platform that helps enterprises discover solutions, engage top talent and drive business outcomes through hackathons, hiring challenges and innovation programs. HackCulture brings together builders, startups, students and enterprises to solve real-world challenges through technology, creating opportunities to build, learn, connect and get noticed."

### Eligibility
Profile Type: Working Professionals (API: profile_type working_professional; gender any; domains []; professional_types []; details "")

### Rules (verbatim, 10 items)
1. Build, don't just pitch - Every submission must include a working prototype or demonstrable build. Slides alone will not qualify.
2. Solve the problem, your way - You may use any reasonable architecture, framework, open-source component or AI model unless a specific challenge states otherwise. What matters is how well you solve the problem.
3. New work only - The core solution must be built during the challenge. Existing libraries, frameworks and your own reusable components are allowed, but they must be declared.
4. Show us how it works - Finalists must submit source code/repository access, a README, architecture overview, models/tools used, key prompts/workflows where relevant, dependencies and instructions required to run the solution.
5. No customer or production data - Only datasets, APIs, sandboxes and credentials explicitly provided or approved for the challenge may be used. No Azentio/customer confidential information may be uploaded to public AI tools.
6. AI is allowed. Blind AI is not - Copilots, LLMs, agents and AI coding tools are encouraged. Teams must disclose the major AI tools/models used and should be able to explain the code, decisions and architecture they submit.
7. Your contribution must be visible - Every team member should be able to explain what they personally built. Azentio.ai may evaluate individual contribution in addition to the overall team solution.
8. We judge what could survive beyond Demo Day - Evaluation will consider problem understanding, working functionality, intelligence/reasoning, architecture, security, usability, originality and ability to scale - not just presentation quality.
9. Build with integrity - Plagiarism, copied submissions, misrepresentation, unauthorised access or inappropriate conduct will result in disqualification.
10. Detailed participation terms - Shortlisted teams will receive the detailed participation terms covering eligibility, judging, IP, confidentiality and data usage.

### FAQs (all 5 expanded, verbatim)
- Q: What is this hackathon really about? A: A chance to prove you can build, not just interview. Solve a real Azentio.ai problem statement and get evaluated on your working prototype.
- Q: Will I actually get hired? A: Top performers get fast-tracked interviews and direct hiring consideration with Azentio.ai, based on business requirements. Participation does not guarantee an offer.
- Q: Is there a fee? A: No. Registration and participation are completely free.
- Q: Can I participate individually or as a team? A: Teams can have up to 3 members. Individual participation is also open, subject to final confirmation from the Azentio.ai team.
- Q: How will I be evaluated? A: Participants will be evaluated on solution quality, technical implementation, innovation, business relevance, and final presentation.
- DISCREPANCY: header/API say team 2-4; FAQ says "up to 3" and "individual participation also open". Confirm with organizers (manvendra@hackculture.in). Also FAQ evaluation list (final presentation) differs from Rule 8 list (architecture, security, scale, etc.) - treat both as signals.

### Support / Contacts
- Manvendra - Program Manager - manvendra@hackculture.in
- HackCulture Support - Support Team - support@hackculture.in
- "Need help? Please contact the event administrator at manvendra@hackculture.in"

### Links on the page
- Azentio website: https://www.azentio.com/
- Azentio LinkedIn: https://www.linkedin.com/company/azentio
- Azentio X: https://x.com/AzentioSoftware
- Event Discord: https://discord.gg/M58Ygk534 (API links.discord; not joined, content unknown)
- HackCulture WhatsApp group (footer, generic HackCulture community, not necessarily event-specific): https://chat.whatsapp.com/GBUGxhbjhaz4xcWhzX5pIu
- HackCulture LinkedIn: https://www.linkedin.com/company/hackculture/ ; Instagram: https://www.instagram.com/hackculture.io/ ; X: https://x.com/Hack_Culture
- Cover image: https://hackcultureplatform.blob.core.windows.net/event-assets/hackathons/6ac35a2947aef38902702d3f/upload_1791463953607_mox13k.webp

### Hidden fields found only in API (not shown on page tabs)
**Registration form questions (all required):**
1. LinkedIn Profile (url, from profile)
2. GitHub / Portfolio (url, from profile)
3. Technical skills (textarea) - "List your key technical skills, separated by commas. E.g. Python, Java, SQL, REST APIs, LLMs, RAG, AI Agents, Docker, Kubernetes, Azure / AWS / GCP."
4. Years of Experience (select 0..12+)
5. Industry / sector background (textarea) - "...E.g. BFSI, Banking, NBFC, Insurance, Fintech, IT Services, SaaS / Product Tech, ERP / Enterprise Software, Healthcare, E-commerce, Telecom, Consulting."
6. Role(s) you are applying for? (checkbox): **Forward Deployed AI Engineer; Senior Forward Deployed AI Engineer; Lead Forward Deployed AI Engineer; Technical Architect - AI & Innovation**
7. Resume (file)
8. Current City (text)
-> KEY INSIGHT: this is a hiring hackathon for Forward Deployed AI Engineer / Technical Architect roles; BFSI/banking/insurance/ERP/AML domain familiarity is signalled as valued; skills list hints at LLMs, RAG, AI agents, Docker/K8s, Azure/AWS/GCP, REST APIs.

**Announcement (posted 2026-10-15, verbatim, abridged header):** "Action Required: Submit Additional Details by 5:00 PM IST Today ... As the next step in the hiring process, all applicants are required to submit a few additional details. Submitting this form is mandatory. Applications without these details cannot be processed further. Fill the form here: https://forms.gle/e5DwNH5evZK5yLnXA  Deadline: 15 October 2026, 5:00 PM IST. Keep ready: registered name and email on HackCulture; role(s) applying for; technical skills and industries; latest resume (PDF or Word); sign in to a Google account to upload." (Signed Team HackCulture.) This is the only announcement.

**Other API fields:** created_at 2026-10-05; organizer_name Azentio.ai; org_id 6ac3597747aef38902702d3e; branding primary_color #07693f; external_registration_url null; override_phase_display_url null; user is_user_eligible true (my anonymous session).

### Raw JSON excerpts (key subset)
```json
{"_id":"6ac35a2947aef38902702d3f","name":"Azentio.ai Build Labs","type":"hackathon","mode":"offline",
 "min_team_size":2,"max_team_size":4,
 "location":{"name":"Bengaluru","address":null,"coordinates":null,"place_id":null},
 "start_datetime":"2026-10-08T14:30:00Z","end_datetime":"2026-10-31T17:30:00Z",
 "eligibility":{"profile_type":"working_professional","domains":[],"details":""},
 "themes":null,"judges":[],"mentors":[],"resources":null,"events":[],
 "links":{"website":"https://www.azentio.com","discord":"https://discord.gg/M58Ygk534","twitter":"https://x.com/AzentioSoftware","linkedin":"https://www.linkedin.com/company/azentio","slack":null,"telegram":null},
 "phases":[
  {"name":"Registration","type":"registration","start_datetime":"2026-10-08T14:30:00Z","end_datetime":"2026-10-25T18:29:00Z","is_elimination_round":true},
  {"name":"Team Formation","type":"team_formation","end_datetime":"2026-10-26T18:29:00Z"},
  {"name":"Final Hackathon Day","type":"submission","is_offline":true,"check_in_required":true,"start_datetime":"2026-10-31T01:30:00Z","end_datetime":"2026-10-31T17:30:00Z","evaluation_metrics":null,"submission_questions":null}],
 "prizes":[{"name":"Winner","value":"150000","currency":"INR"},{"name":"Runner-up","value":"90000"},{"name":"Second Runner-up","value":"60000"},{"name":"Job Opportunities","type":"job_offer"}],
 "total_participants":1731,"is_registration_open":false,"flags":{"team_directory":true},"resolved_flags":{"ai_judging":false}}
```
(Full JSON can be re-fetched at the API URL above; it is ~15.5 KB.)

### Other HackCulture pages
- https://hackculture.io/programs lists "Azentio.ai Build Labs - Oct 8 - Oct 31 - Azentio.ai" under FEATURED only. No other Azentio program pages. Programs list shows it alongside unrelated events (GAVS Hackathon, CyberForge, Sarvam BuildIn' Hours, etc.).
- The page itself loads data client-side from the API; no `__NEXT_DATA__` (Next.js app router). No extra XHRs beyond the hackathon GET and a `/event/hackathon/{id}/view` tracking call.

---
## UNVERIFIED / NOT FOUND
- Exact venue / address / floor / map: NOT published (city only: Bengaluru). Likely to be sent to shortlisted teams by email/Discord/WhatsApp. UNVERIFIED.
- Problem statements / theme tracks / datasets / APIs / sandboxes: NOT published; "revealing soon" as of 2026-10-28/29 page update. Presumably revealed at/just before the 31 Oct Grand Finale or in Discord/email. UNVERIFIED.
- Mentors, judges names: none published (arrays empty). Only "Azentio's technology leaders" generically.
- Team size: 2-4 (header) vs "up to 3" (FAQ) - unresolved.
- Whether Discord/WhatsApp contain event info: not opened (joining a group is out of scope for this research task).
- Whether participants must be shortlisted to attend 31 Oct: page text says "Shortlisted teams will advance to the Grand Finale"; registration needed approval. Check-in required on the day.
- Web search (3 queries) and Luma calendar (https://luma.com/hackculture) returned nothing about this event; no LinkedIn / Instagram / X / Unstop / Devfolio posts found via search tool. Social platforms themselves were not logged into / browsed.
- Per the Overview image alt "Azentio Tech Catalyst 2026" - this suggests a template reuse from another event ("Bessemer Tech Catalyst" is a separate HackCulture program); do not infer anything from it.

## Practical implications (inference, flagged as such)
- INFERENCE: Because the form targets "Forward Deployed AI Engineer" roles, expect problem statements in BFSI/enterprise workflows (banking, insurance, ERP, AML, document intelligence, agentic automation, decisioning) - the Overview names "intelligent automation, AI agents, decisioning, document intelligence, customer experiences". Not confirmed.
- Prepare: a reusable agent/RAG scaffold, README + architecture template, AI-tool disclosure list, per-member contribution notes; avoid real/customer data; use only provided datasets.
- Ask organizers (manvendra@hackculture.in) for venue, reporting time/check-in, wifi/power, datasets/APIs, allowed tools, and team-size rule.
