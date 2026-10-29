# F: Capital-markets hackathon winners, the product landscape, and Azentio's capital-markets stack

Research date: 2026-10-29. Every fact has a URL next to it. Anything I inferred is marked **HYPOTHESIS**. Anything I could not verify is marked **NOT VERIFIED**.
Access note: azentio.com fails TLS verification in WebFetch ("unable to verify the first certificate"), so I read its pages through `curl -k` and extracted the text locally. The content matches the live pages.

---

## Part A: Azentio capital markets

### A.1 Headline facts
- Azentio calls MFund Plus its "flagship" product. It describes it as a "fully integrated platform that unifies front-to-back office operations across asset management, investor services, and wealth management". https://www.azentio.com/capital-markets
- Impact numbers on the page are animated counters, so I read them from the image alt text and filenames:
  - **80+ customers**
  - **~50% "of AUM managed by Mutual Funds in India is processed by MFund"**
  - **"7 out of Top 15 fund houses in India use MFund"**
  
  Source: https://www.azentio.com/capital-markets (image assets `80.svg`, `50-percentage-icon.svg`, `7.svg`).
- MFund Plus is "Trusted by 80+ leading global banks and asset managers" and "manages over $400 billion in AUM". https://www.azentio.com/capital-markets/azentio-mfund-plus
- A 2022 press release quotes Azentio: "MFund Plus is a trusted solution in the Asian markets for more than two decades". Azentio is Singapore-headquartered and owned by funds advised by Apax Partners. The company had 800+ clients in 60+ countries and about 2,400 staff at the time. https://news.webindia123.com/news/Articles/Business/20220221/3909683.html
- A search-engine snippet says Azentio's site once used the name "Azentio ONECapitalMarkets (erstwhile MFund Plus)". That URL (https://www.azentio.com/onecapitalmarkets) now redirects to the homepage, so this is a past or unused brand. **NOT VERIFIED** on a live page.
- The site footer lists "Capital markets: MFund plus / MFund plus WMS / **MFund RS**". In the HTML, the "MFund RS" link points to `/capital-markets/azentio-mfund-iss` (capital-markets.html, line 1535). https://www.azentio.com/capital-markets

### A.2 What each product does

| Product | Azentio's own words | Plain words | Likely users | Evidence on markets |
|---|---|---|---|---|
| **MFund Plus** (investment management) | "end-to-end support across the entire investment lifecycle—from dealing to compliance, mid-office, accounting, and valuation". Features: "World-class compliance engine", "Advanced accounting and valuation", "portfolio simulators and rebalancers", "Streamlined order management", "Custom report engine (DQE)", "slice-and-dice report writing and auto task scheduling". https://www.azentio.com/capital-markets/azentio-mfund-plus | The AMC or fund house's core system for the fund-manager and back-office side. It places and books orders, checks every trade against regulatory and internal investment limits before and after it is done, runs the fund accounting, and computes valuations and NAV. | Asset management companies (AMCs), banks, and asset managers | India: Samco Mutual Fund went live (Feb 2022) on MFund Plus for front-office processes. The scope included "automation of SEBI-mandated guidelines and internal audit policies", an Order Management module for equity and debt, and the report engine. The release says "All relevant SEBI directives have been configured to detect regulatory breaches". https://news.webindia123.com/news/Articles/Business/20220221/3909683.html |
| **MFund ISS** (fund administration and investor services) | "manage the entire investor servicing lifecycle. From onboarding to registry transactions, agency, distribution, and digital channels". It handles "subscriptions, redemptions, switches, and transfers", offers a "Dedicated agent portal", and produces "reports and investor statements". https://www.azentio.com/capital-markets/azentio-mfund-iss | A registrar and transfer-agency system for fund units. It keeps the register of who owns units, processes buy, sell, switch and transfer requests, manages distributors and agents, and issues investor statements. | AMCs that run their own transfer agency, fund administrators, and possibly RTAs. **HYPOTHESIS:** in India most mutual-fund RTA work sits with the large RTAs, so ISS is more likely sold to in-house TAs in SEA and the Middle East. This is not verified. | The page does not name a market. |
| **MFund RS** | Only a nav label that links to the ISS page. https://www.azentio.com/capital-markets | **HYPOTHESIS:** "RS" stands for Registry Services, as an alias or variant of ISS. No dedicated page exists. | Same as ISS | None |
| **MFund Plus WMS** (wealth management) | "from relationship management and branch onboarding to goal-based financial planning, transactions, and reporting". Features: "built-in CRM", "Digital onboarding", "multi-goal, life event, and market simulations", "Predictive analytics & automation", "360º customer view", "Revenue & incentive management", "Robo advisor … AI-driven insights", and web and mobile apps. https://www.azentio.com/capital-markets/azentio-mfund-plus-wms-wealth-mgmt | A bank or private-wealth advisory platform. It covers relationship-manager CRM, client onboarding, goal planning, robo-advice, advisor commissions, and client portals. | Banks' wealth arms, private banks, and distributors | Philippines: Philippine National Bank (PNB) implemented MFund Plus WMS. https://www.azentio.com/insights/case-studies-and-testimonials/philippine-national-bank |

- **Is it a brokerage back office?** I found no broker, clearing or settlement product on Azentio's capital-markets pages. The products cover asset management, investor services and wealth. https://www.azentio.com/capital-markets
- **Middle East:** I found no MFund-specific Middle East customer on the pages I read. Azentio's case-study list includes Gulf insurance and credit clients ("How QIIC modernized insurance operations…", "How Bahrain Cr…"), but they are not capital-markets clients. https://www.azentio.com/insights/case-studies-and-testimonials/philippine-national-bank

### A.3 Pain points Azentio itself states
The PNB case study lists these: "Manual onboarding and advisory processes limited branch efficiency", "Longer time-to market for new investment products", "Fragmented systems for risk profiling and lifecycle management", and "Lack of data-driven tools for personalized financial planning". On outcomes it says "embedded, traceable workflows enhance compliance and governance". https://www.azentio.com/insights/case-studies-and-testimonials/philippine-national-bank
The Samco release says the system had to cover "audit, regulatory, and internal MIS needs" and SEBI directives. https://news.webindia123.com/news/Articles/Business/20220221/3909683.html

### A.4 AMLOCK features relevant to securities
- **"Trade-based AML" means trade finance, not securities trading.** The page says it screens "parties, vessels, ports, dual-use goods, and trade anomalies" and detects "over- or under-invoicing, and false goods declarations". https://www.azentio.com/risk-compliance/trade-based-anti-money-laundering
- **Other AMLOCK modules:** KYC & onboarding, Transaction monitoring ("analyzes financial transactions in real-time"), Sanctions screening (OFAC, EU, UN), Fraud detection ("monitors all banking channels"), Regulatory reporting, Investigation ("automated workflows, documentation, and collaboration tools"), and Advanced analytics ("harnesses AI and machine learning to detect hidden AML risks"). https://www.azentio.com/risk-compliance/trade-based-anti-money-laundering
- **Market abuse or trade surveillance (spoofing, insider trading):** none of the AMLOCK pages I read mention it. The fraud module is described for "banking channels". **HYPOTHESIS:** securities-market abuse surveillance is a gap in Azentio's stack that a hackathon project could fill.
- **Recognition:** Chartis Category Leader in AML Transaction Monitoring 2026, and in Watchlist and Adverse Media Monitoring 2026. QKS SPARK Matrix AML 2026 Leader. https://www.azentio.com/capital-markets
- **Testimonials:** Razorpay (Head of Risk) and Bajaj Finance (Head of IT). https://www.azentio.com/risk-compliance/trade-based-anti-money-laundering

### A.5 Where agentic AI could plug in (all HYPOTHESIS)
1. **MFund Plus compliance engine, circular-to-rule agent.** It would read SEBI or other regulator circulars on investment limits, propose rule configurations for the compliance engine, and route them to a compliance officer for sign-off. This matches what Samco went live for ("SEBI directives … configured to detect regulatory breaches") and the SEBI TechSprint 2026 winning pattern in B.1.
2. **NAV and valuation exception agent.** It would explain stale or missing prices, corporate-action mismatches, and reconciliation breaks, then propose fixes for approval. This mirrors the DTCC winners on post-trade exceptions in B.3.
3. **ISS investor-servicing agent.** It would triage redemption, switch and transfer requests and failures (KYC, bank-mandate or nominee issues), draft investor replies, and resolve distributor commission queries.
4. **WMS RM copilot with suitability guardrails.** It would produce next-best-action suggestions plus an automatic check of suitability and risk-profile limits before the RM sends advice.
5. **AMLOCK x ISS investor-side AML.** It would flag folio or unit patterns such as rapid subscribe-redeem cycles or third-party payouts, draft the STR narrative, and leave a human decision step.
6. **Broker surveillance-alert agent for small brokers.** This is a new segment for Azentio (see C.2).

---

## Part B: What won capital-markets and securities hackathons

### B.1 SEBI Securities Market TechSprint 2026 (GFF 2026, Mumbai): the most relevant
**Official problem statements, verbatim titles.** Source: https://www.globalfintechfest.com/gff-hackathons/sebi-techsprint
1. Investor Protection: **"AI-Driven Detection of Synthetic Media and Phishing Attacks in Securities Markets"**
2. RegTech: **"Agentic Compliance — From Regulatory Text to Operational Action"**. The brief is to "Turn SEBI's regulatory text into structured, machine-actionable, auditable compliance logic for market intermediaries" and it suggests using SEBI master circulars for stockbrokers and investment advisers.
3. WealthTech: **"Super App for Unified Multi-Asset Investing and Awareness for Retail Investors"**
4. Fund Raising: **"Simplifying IPO Offer Document Preparation for SMEs"**

**Evaluation criteria:** Market Impact, Technology Stack (AI/ML/Blockchain/NLP/DPI), Feasibility, Scalability, and Alignment with SEBI's Mandate. **Prizes:** ₹2.5L, ₹2L and ₹1.5L, plus ₹50k jury awards. https://www.globalfintechfest.com/gff-hackathons/sebi-techsprint

**Winners.** Source: SEBI PR No.57/2026 dated 11 Sep 2026, as reported by https://taxguru.in/?p=1078660

| Rank | Solution | Problem statement |
|---|---|---|
| 1st | **NIYAMA** (Kellton) | Agentic Compliance |
| 2nd | **IPO SHERPA** | SME IPO offer document |
| 3rd | **SEBI ImpactOS** | Agentic Compliance |
| Jury | SEBI Kavach | Synthetic media / phishing |
| Jury | Vantage; North Star-Invest | Super App |
| Jury | SIIM – SME IPO Intelligence Mitra | SME IPO |

- **What NIYAMA built:** a "compliance compiler" that parses each circular clause into executable "rules-as-code". It runs on a network of agents and adds compliance-officer sign-off on every rule, "continuous evidence binding, breach detection, and a hash-chained audit trail". https://cxotoday.com/media-coverage/kellton-wins-first-prize-at-sebis-securities-market-techsprint-2026-turning-regulation-into-code-with-agentic-ai/
- **Scale of the contest:** 525 teams registered, 340+ built prototypes, 145 reached the demo stage and 25 reached the jury round. The source does not state the jury's reasoning. https://cxotoday.com/media-coverage/kellton-wins-first-prize-at-sebis-securities-market-techsprint-2026-turning-regulation-into-code-with-agentic-ai/
- **Takeaway:** two of the top three entries went to Agentic Compliance.

### B.2 SEBI Securities Market Hackathon 2025 (GFF 2025)
- **Partners:** SEBI with BSE, CDSL, NSDL and KFintech. **Problem areas** (labels only): "fraud prevention", "enhancing retail investor education & engagement", "improving liquidity in bond markets", "member compliance monitoring". https://www.outlookbusiness.com/markets/sebi-launches-securities-market-hackathon and https://www.taxmann.com/post/blog/sebi-launches-securities-market-hackathon-at-global-fintech-fest
- A search-result snippet says the compliance-monitoring problem noted that small and medium brokers struggle to deploy systems for compliance and client-behaviour monitoring. **NOT VERIFIED** on the source page.
- **Known winner:** an IIIT Bangalore student won a ₹25,000 Jury Recommendation Prize for an "AI-powered fraud detection system". The awards were held on 8 Oct 2025. https://naviiina.iiitb.ac.in/?p=10234
- I found no official list of the top three.

### B.3 SEBI as a winner: Fii C:>DIR Global "Agentic Regulator" Hackathon 2026
- **Scale:** 336 submissions, 942 people, 65+ countries and six problem spaces, including "AI-driven fraud, agentic payments oversight, and market manipulation".
- **Winner:** SEBI's Team Pheonix with **PolicyTwin**, for USD 35,000. PolicyTwin is an AI "practice market" in which agent personas (retail investors, institutions, brokers, HFTs and bad actors) place orders so the regulator can test a draft rule. It checks for manipulation, margin shortages and retail losses, then tests safeguards. "humans remain firmly in control … Findings … are never acted on automatically."
- **Source:** SEBI PR No.63/2026, 14 Oct 2026. https://www.sebi.gov.in/sebi_data/attachdocs/oct-2026/1791985275670.pdf

### B.4 Innovate.DTCC AI Hackathon (with FINOS)

**2025 edition.** Source: https://www.dtcc.com/dtcc-connection/articles/2025/april/02/dtcc-announces-winners-from-first-ai-powered-hackathon

| Award | Team | What they built |
|---|---|---|
| Gold, $100k grant | CIBC, "Automated Regulatory Change Management Solution" | Automates retrieval of regulatory updates; CIBC estimates it saves "months of work" per person per year |
| Silver, $75k | Cyber ThirdEye, "Third-Party Cybersecurity Risk Scoring Platform" | Vendor cyber-risk scores on a CISO dashboard |
| Bronze, $40k | Xypher (Deutsche Bank), "AI-Powered Trade Settlement System" | Trade verification and error detection, liquidity forecasting, and an AI agent that flags "daisy chain" settlement failures |
| Academic, $40k | Duke "Cipher Sentinel", "AI-Powered Anti Money Laundering for Digital Wallets" | AI monitoring of digital wallets for suspicious activity |
| Vendor award | Accenture, "Automated Regulatory Compliance" | GenAI review of regulatory documents against internal controls |

**2026 edition.** Six tracks: IT Innovation; Financial & Cyber Risk Intelligence; Regulatory Compliance & Governance; Generative AI for Finance; Employee & Customer Experience AI; Internal Audit & Assurance. Source: https://www.dtcc.com/dtcc-connection/articles/2026/march/26/innovate-dtcc-2026-industry-powered-ai-hackathon-winners

| Award | Team | What they built |
|---|---|---|
| Gold, $100k | Snowflake + DTCC | Agentic AI threat-hunting tool queried in plain language |
| Silver, $75k | **NovaMind** (Deutsche Bank) | Automates **post-trade exceptions** through an "auditable" **multi-agent pipeline** |
| Bronze, $40k | OpsFlow | Compliance automation on the FINOS CALM standard |
| Internal Audit Gold, $35k | WMATA | Cross-agency audit insights and risk-based audit planning |

### B.5 Other relevant events
- **IFSCA / GIFT City "Sprint04: Market-Tech (Capital Markets)" (I-Sprint'21, NSE-sponsored, ₹20 lakh pool).** Winners were BondEvalue (₹10L), Decimal Point Analytics (₹6L) and Snapper Future Tech (₹4L). The corrigendum does not describe what they built. https://www.IFSCA.gov.in/Document/Legal/revised-press-release_markettech-winners31082022012624.pdf
- **SEBI/NISM Investors Hackathon (2023).** A college document says a team won 2nd prize (₹75,000) with "Fraud Shield". **NOT VERIFIED** which edition or official title this was. https://skcet.ac.in/wp-content/uploads/2023/11/Hackathon-Book_CSE.pdf. Related event page: https://www.nism.ac.in/event/investor-awareness-hackathon-2023
- **SEBI Empowering Investors Hackathon (2023, Hack2skill).** Prizes were ₹1L, ₹50k and ₹25k. I found no winners. https://hack2skill.com/hack/sebi-empowering-investors-hackathon
- **MAS Global FinTech Hackcelerator 2026.** The problem statements, verbatim, are GXS Bank: "integrating credit and fraud risk modelling in digital banking"; Julius Baer: "reimagining of wealth management for a digitally native generation"; Zurich: "empowering SMEs to better assess, quantify and proactively manage their business risk exposure". Winners are due 19 Nov 2026, with S$80k each. https://www.mas.gov.sg/news/media-releases/2026/mas-announces-finalists-for-the-2026-global-fintech-hackcelerator-and-fintech-excellence-awards. The 2025 edition was themed "AI for Financial Services". https://www.mas.gov.sg/news/media-releases/2025/mas-announces-finalists-for-the-2025-global-fintech-hackcelerator-and-fintech-excellence-awards
- **NOT VERIFIED or not found this session:** Smart India Hackathon SEBI problem statements, BSE/NSE/NSDL standalone hackathon winners, and Nasdaq, LSEG, Euronext and SGX hackathon winners. My searches found nothing citable.

### B.6 Patterns across the winners (HYPOTHESIS, drawn from the facts above)
- **Regulation-to-executable-rules** wins repeatedly: CIBC (DTCC 2025 Gold), Accenture (DTCC 2025), and NIYAMA and SEBI ImpactOS (SEBI 2026, 1st and 3rd).
- **Multi-agent post-trade and exception handling** places in the top three: Xypher (2025 Bronze) and NovaMind (2026 Silver).
- **Every winner stresses human control and auditability:** NIYAMA's sign-off plus hash-chained audit trail, PolicyTwin's "never acted on automatically", and NovaMind's "auditable" pipeline.

---

## Part C: Product landscape for surveillance and compliance

### C.1 Incumbents

| Vendor / product | What it does (cited) | Source |
|---|---|---|
| **NICE Actimize SURVEIL-X** | Trade and communications surveillance. GenAI ("Actimize Intelligence", May 2025) reads jargon, tone and intent across email, chat and voice. Vendor claims up to 85% fewer false positives and 4x more true misconduct found. | https://www.businesswire.com/news/home/20250528200491/en/NICE-Actimize-Empowers-SURVEIL-X-with-Generative-AI-Launching-a-New-Era-in-Market-Abuse-and-Conduct-Risk-Detection |
| **Nasdaq SMARTS / Trade Surveillance** | Market-abuse surveillance. GenAI added (May 2024, on Amazon Bedrock) to triage alerts for manipulation and insider dealing and to summarise filings, news and sentiment. In a PoC, analysts estimated 33% less investigation time. | https://ir.nasdaq.com/node/107521 ; https://www.nasdaq.com/products/fintech/market-surveillance |
| **Eventus Validus** | Trade surveillance, algo monitoring and market risk. 25% client growth in 2024 and clients on six continents. Plans more AI use. | https://fintech.global/2024/01/31/eventus-outlines-its-aim-to-redefine-trade-surveillance/ |
| **Global Relay** | Archiving plus AI-enabled communications surveillance (Nov 2024). LLM risk analysis and transcription in 50+ languages. | https://www.businesswire.com/news/home/20241112420017/en/Global-Relay-Announces-Next-Gen-AI-Enabled-Communications-Surveillance |
| **Behavox** | AI and ML over emails, calls, trade data and chats for surveillance and compliance. | https://www.behavox.com/?p=4004 |
| **TrackWizz (TSS Consultancy, Mumbai, est. 2007)** | Sanctions and watchlist screening, "transaction monitoring for AML & surveillance", risk rating and EDD, FATCA/CRS, and insider trading. Upstox adopted its real-time AML screening product Screenzaa (Oct 2024). It claims 350+ BFSI entities (sponsored release). | https://www.cbinsights.com/company/tss-consultancy ; https://www.theweek.in/wire-updates/business/2024/10/22/dcm15-tss-consultancy.html |
| Trading Technologies, Signzy, Kaleidofin | **NOT VERIFIED** this session. I have no citations for them, so I made no claims about them. | none |

### C.2 Regulatory pull in India (small and mid-size brokers)
- SEBI's Stock Brokers (Amendment) Regulations, 2024 require an "Institutional Mechanism for Prevention and Detection of Fraud or Market Abuse". It covers surveillance systems, internal controls, escalation and reporting, and a whistle-blower policy. Deadlines are phased by active UCCs: >50,000 by 1 Jan 2025, 2,001 to 50,000 by 1 Apr 2025, and **up to 2,000 by 1 Apr 2026**. https://moneylife.in/article/sebi-asks-stockbrokers-to-follow-institutional-mechanism-to-prevent-and-detect-fraud-market-abuse/74571.html ; https://conventuslaw.com/report/india-obligations-placed-on-stockbrokers-to-curb-fraud-and-money-laundering/
- One summary says brokers must report suspicious activity to exchanges within 48 hours. **NOT VERIFIED** against SEBI's text. https://conventuslaw.com/report/india-obligations-placed-on-stockbrokers-to-curb-fraud-and-money-laundering/
- Brokers' surveillance policies cite exchange alert channels: BSE e-BOSS for regulatory alerts and NSE ENIT for transactional alerts. A Nirmal Bang policy also cites a SEBI Master Circular on Surveillance last updated 15 May 2026. https://aryafingroup.in/wp-content/uploads/2025/01/Surveillance-Policy.pdf ; https://www.nirmalbang.com/NBSPL_SURVEILLANCE_POLICY_1.3_190826.pdf

### C.3 Gaps an AI agent could fill (HYPOTHESIS)
- **Small and mid-size Indian brokers:** they now carry surveillance obligations (C.2) but have only analyst headcount for global-tier tools like SMARTS or Actimize. An agent could:
  - pull exchange alerts,
  - gather client KYC, trade, ledger and fund-flow evidence,
  - draft the alert disposition with reasons,
  - route borderline cases to a human, and
  - log a tamper-evident audit trail.
  
  This merges SEBI 2025 PS "member compliance monitoring" with SEBI 2026 PS2.
- **AMCs on MFund Plus:** a circular-to-compliance-rule agent with officer sign-off, the NIYAMA pattern applied to MF investment-limit rules.
- **RTAs and AMCs on ISS:** investor-servicing and exception agents, plus investor-side AML (mule folios, third-party redemptions) linked to AMLOCK.
- **Distributors and wealth (WMS):** a suitability and mis-selling guard on RM recommendations, and an agent that explains commissions and incentives.
- **Middle East and SEA:** Arabic and multilingual communications review. Global Relay offers 50+ languages, but its fit and pricing for regional mid-size firms is **NOT VERIFIED**.

---

## What judges from a capital-markets software vendor would most likely reward (HYPOTHESIS, 6 bullets)
1. **A plug-in to their actual stack.** The best fit is an agent that sits beside MFund Plus (compliance and valuation), ISS (investor servicing) or AMLOCK (alerts and STRs) through a clear API or event boundary, rather than a standalone trading bot. Their pages stress "Seamless integration".
2. **Regulation turned into working, auditable logic.** Take a real SEBI master-circular clause, turn it into a rule, show the rule catching a breach, and show the evidence. This is the pattern that won SEBI TechSprint 2026 (NIYAMA, ImpactOS) and DTCC 2025 (CIBC).
3. **A human in the loop and a tamper-evident audit trail.** Agents propose and humans approve. Show sign-off gates and hash-chained logs, as NIYAMA and PolicyTwin do. A regulated-software vendor cannot ship anything else.
4. **Measured operational savings on a pain point they already name.** For example: alert-triage minutes per case, false-positive rate, or exception turnaround time, benchmarked the way Nasdaq claims "33%" and Actimize "85%". Ground it in the manual-process pain points they list (PNB case).
5. **India-first realism with a regional path.** Use Indian MF and broker data shapes (folios, UCCs, NSE/BSE alerts) plus a credible story for the Middle East and SEA, where Azentio sells.
6. **Production-grade engineering signals, since the event is hiring-focused.** That means a multi-agent design with clear tool contracts, evaluation and test sets, failure handling, and data privacy (PII masking). It should be a clean, demo-able end-to-end flow rather than a slide deck.
