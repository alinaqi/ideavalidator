# Idea & Validation Frameworks — survey and the stack we use

**Compiled 2026-10-31** from ~45 web searches (research agent) plus the Palgu PDLC v5. Primary sources
linked where found; secondary summaries flagged. Read with `docs/WORKFLOW.md`: Section 0 below maps
the stack onto the nine pipeline stages.

Unconfirmed items: a Rand Fishkin "zebra" framing (no source found; SparkToro was profitable ~10 months
post-launch, not day one, per https://conversion-rate-experts.com/sparktoro-testimonial/), and the exact
"Innovator's Gift" wording in Running Lean 3rd ed. (summary site only). Lenny's Newsletter PMF material
is largely paywalled; only public pieces are cited.

Stage key: **I** idea · **P** problem · **M** market · **C** customer/ICP · **W** pricing/WTP ·
**S** solution · **G** GTM · **$** profitability/business design.

---

## 0. How the stack maps onto our pipeline

| Pipeline stage | Frameworks applied inside the prompt | Real-world framework the founder runs afterwards |
|---|---|---|
| `frame` | Lean Canvas (Maurya), Opportunity Solution Tree framing (Torres), PG schlep/annoyance test, YC tarpit screen, Cohen "Ideal Bootstrapped Business" checklist | — |
| `problem` | Cohen "Is there a problem?" criteria, Sequoia Arc archetype, demand-proxy triangulation (Part 4), Mom Test guide | 10-15 Mom Test interviews, log commitments |
| `market` | Tringas 5x rule, bottom-up sizing (Aulet), wedge patterns (Dixon), a16z/Bessemer vertical-AI lens (price against the services line) | Confirm top two channels are reachable |
| `icp` | Lenny ICP test, Kazanjy narrative ICP, Crossing the Chasm beachhead, Disciplined Entrepreneurship segmentation, PDLC Research Coverage roles | Build 50-named-account list |
| `swot` | SWOT → TOWS, Helmer 7 Powers (counter-positioning, cornered resource) | — |
| `wtp` | Van Westendorp + Gabor-Granger design, replaced-labour-cost anchor, PDLC Experiment Protocol for a pre-sale | Kagan 3-paid-in-48h / 5 paid pilots or LOIs with deposits |
| `economics` | PG default alive, Cohen cash-machine criteria, Walling stair-step, Bland & Osterwalder evidence strength | Replace estimates with real numbers |
| `risks` | PDLC Assumption & Risk Map + Experiment Router, Savoia xyz hypotheses, Bland & Osterwalder experiment menu | Run the two-week plan |
| `decision` | PDLC Bet Portfolio record, Dunford positioning canvas, Jackson 4 P's as pivot checklist | Founder decision in writing; concierge/vibe-coded MVP only after money |

---

## 1. Frameworks, ranked by usefulness for bootstrapped, profitable-from-day-one validation

1. **Jason Cohen, "Excuse me, is there a problem?" (2023)** — https://longform.asmartbear.com/problem/ · Score a target segment on multiplying power-of-ten criteria: Plausible, Self-Aware, Lucrative, Eager, Enduring; product ≥1 is viable for an indie business, ≥2 for a scale-up. LLM skill version: https://skills.asmartbear.com/skills/asb-problem/. **Stages: P, M, C, $.** *Desk+LLM:* Have the LLM Fermi-estimate each criterion from job-post counts, forum threads and pricing pages, then override with real numbers.

2. **Jason Cohen, "Designing the Ideal Bootstrapped Business" (MicroConf 2013)** — notes: https://mtlynch.io/notes/designing-the-ideal-bootstrapped-business/ ; 2023 AI-era update: https://www.startupsfortherestofus.com/episodes/episode-817-bootstrapping-in-the-age-of-ai-with-jason-cohen · The "cash machine" checklist: recurring revenue, annual prepay, B2B, no one-off pain (weddings), naturally recurring problem, $50-$500/mo price. **Stages: $, M.** *Desk+LLM:* Score every candidate idea against the checklist before any customer work.

3. **Noah Kagan, Million Dollar Weekend (2024), "3 paying customers in 48 hours"** — https://mastersofscale.com/people/noah-kagan ; https://wealthtender.com/insights/three-essential-takeaways-from-million-dollarweekend/ · Pre-sell to 3 people who pay real money before building. **Stages: S, W, G.** *Desk+LLM:* LLM drafts the offer, DM scripts and one-page order form; you send them to a hand-built list.

4. **Rob Fitzpatrick, The Mom Test (2013)** — summary: https://www.ybrikman.com/blog/2023/03/29/the-mom-test/ · Three rules (their life not your idea; specifics in the past; listen) plus "commitment and advancement": a meeting only counts if the prospect gives time, reputation or money. **Stages: P, C.** *Desk+LLM:* LLM generates the question guide and scores transcripts for compliments vs commitments; never let it generate the answers.

5. **Alberto Savoia, The Right It / pretotyping** — https://stvp.stanford.edu/av/build-right-it-entire-talk ; summary https://www.productcompass.pm/p/how-to-build-the-right-product-with · XYZ hypothesis ("At least X% of Y will Z"), narrowed to a testable "xyz", Skin-in-the-Game data only. **Stages: M, S.** *Desk+LLM:* LLM turns each idea into 3 xyz hypotheses and designs the fake-door/landing test; you run it.

6. **Bland & Osterwalder, Testing Business Ideas (2019)** — https://www.strategyzer.com/library/testing-business-ideas-book-summary · 44 experiments rated by cost, time and evidence strength (interviews weak; pre-sales and crowdfunding strongest), tied to desirability/feasibility/viability. **Stages: all.** *Desk+LLM:* The menu: LLM maps your riskiest assumption to the cheapest strong-evidence experiment.

7. **Ash Maurya, Lean Canvas + Running Lean 3rd ed. (2022)** — https://oreilly.com/library/view/running-lean-3rd/9781098108762 · One-page model stress-tested for desirability, viability, feasibility; 3rd ed. adds continuous innovation and "innovator's bias" (love the problem, not the solution). **Stages: I, P, $.** *Desk+LLM:* LLM drafts 3 competing canvases per idea; kill the ones where channels and revenue are hand-waving.

8. **Rob Walling, Stair Step Method + The SaaS Playbook (2023) + TinySeed data** — https://microconf.com/latest/the-stairstep-approach-to-bootstrapping ; https://www.startupsfortherestofus.com/episodes/episode-812-the-2025-state-of-tinyseed · Step 1: one product, one marketing channel; step 2: repeat until you own your time; step 3: standalone SaaS. **Stages: I, G, $.** *Desk+LLM:* A day-one-profitable idea should be a step-1 or step-2 business.

9. **Tyler Tringas, Micro-SaaS ebook** — https://tylertringas.com/micro-saas-ebook/ · 5x cheaper or 5x better than what people already pay for; don't invent categories; retention first; one solo-manageable niche. **Stages: I, M, $.** *Desk+LLM:* Scan app marketplaces, G2 and Capterra for incumbents whose reviews reveal the "5x" gap.

10. **Sequoia Arc PMF Framework (2023)** — https://sequoiacap.com/article/pmf-framework · Hair-on-Fire (urgent, crowded: win on speed + GTM), Hard Fact (tolerated inefficiency: quantify and overcome inertia), Future Vision (new market: not for bootstrappers). **Stages: M, G.** *Desk+LLM:* Day-one profit nearly always means Hair-on-Fire or a very quantified Hard Fact.

11. **Lenny Rachitsky, ICP definition + Pete Kazanjy, Founding Sales** — https://www.lennysnewsletter.com/p/how-to-identify-your-ideal-customer ; https://www.holloway.com/g/founding-sales/sections/early-prospecting · An ICP is one segment where the problem's value and the way to reach them are both uniform; narrative first, abstraction later; founder closes the first ~20 personally. **Stages: C, G.** *Desk+LLM:* LLM builds a 3-attribute ICP and a list of 50 named accounts; you validate by outreach reply rate.

12. **Chris Dixon, "Thin edge of the wedge" + wedge patterns** — https://cdixon.org/2010/12/26/the-thin-edge-of-the-wedge-strategy ; https://every.to/divinations/product-wedges-a-complete-guide · Enter via one narrow, painful, under-served problem; name the two segments you expand into next. **Stages: G, M.**

13. **Rahul Vohra / First Round, Superhuman PMF Engine + Sean Ellis 40% test** — https://review.firstround.com/how-superhuman-built-an-engine-to-find-product-market-fit/ ; https://www.lennysnewsletter.com/p/how-to-know-if-youve-got-productmarket · "Very disappointed" %, segment by who loves you. **Stages: S, C.** Useful only once ~40+ real users exist.

14. **Todd Jackson / First Round PMF Method (four levels)** — https://www.lennysnewsletter.com/p/a-framework-for-finding-product-market · Nascent → Developing → Strong → Extreme; when stuck revisit the four P's (persona, problem, promise, product). **Stages: C, P, S.** Use the 4 P's as the pivot checklist.

15. **Dalton Caldwell & Michael Seibel, Tarpit Ideas (YC)** — https://www.lennysnewsletter.com/p/lessons-from-1000-yc-startups ; https://blog.matt-rickard.com/p/tarpit-ideas · Warm feedback, structural failure. **Stages: I.** *Desk+LLM:* Ask for the 10 most recent dead companies attacking the same idea and why; verify on Crunchbase/Wayback.

16. **YC Requests for Startups (Winter 2027 list, Oct 2026)** — https://www.ycombinator.com/rfs · Themes: robots made in America, vertical foundation models, AI for city hall, data-center supply chain, "own your intelligence". Mostly VC-scale; mine each for small, boring sub-problems a solo founder can serve profitably. **Stages: I, M.**

17. **Paul Graham, "How to Get Startup Ideas", "Schlep Blindness", "Default Alive or Default Dead?"** — https://paulgraham.com/startupideas.html ; https://paulgraham.com/schlep.html ; https://paulgraham.com/aord.html · Notice your own problems; live in the future; do the tedious thing others avoid; know spend/revenue/growth at all times. **Stages: I, $.** Keep a weekly annoyances log.

18. **Greg Isenberg, Audience-Community-Product + subreddit mining** — https://www.antoinebuteau.com/lessons-from-greg-isenberg/ (secondary; primary is the Startup Ideas Podcast) · Every subreddit is a pre-validated group with a shared pain. **Stages: I, C, G.** *Desk+LLM:* Summarise top complaints per subreddit over 12 months; count distinct complainers, not upvotes.

19. **Arvid Kahl, The Embedded Entrepreneur + Zero to Sold** — https://bootstrappedfounder.gumroad.com/l/embedded-entrepreneur · Audience discovery and exploration before any product. **Stages: C, I.** Embed in the niche's communities for 30 days.

20. **Teresa Torres, Opportunity Solution Tree** — https://www.producttalk.org/ · Outcome → opportunities → solutions → experiments; weekly customer touchpoints. **Stages: P, S.** Stops the jump to solutions (also the PDLC's own Opportunity Solution Map basis).

21. **April Dunford, Obviously Awesome** — https://www.aprildunford.com/ · Positioning from competitive alternatives, unique attributes, value, best-fit customers, market category. **Stages: C, G, W.** Test the story in sales calls.

22. **Van Westendorp PSM + Gabor-Granger** — https://conjointly.com/blog/gabor-granger-or-van-westendorp ; https://www.getmonetizely.com/articles/van-westendorp-vs-gabor-granger-for-saas-which-pricing-methodology-to-choose · VW for the acceptable band (early), GG for the revenue-optimal point (~30 respondents gives a first read). The methods can diverge; reconcile against actual pre-sale behaviour. **Stages: W.** Respondents must be real ICP members.

23. **Hamilton Helmer, 7 Powers** — https://www.theinvestorspodcast.com/episodes/7-powers-by-hamilton-helmer/ (summary) · Only counter-positioning and cornered resource are available at origination. **Stages: M, $.** *Desk+LLM:* Make the LLM argue the incumbent's case for *not* copying you; if it cannot, you have no power.

24. **a16z "Vertical SaaS: Now with AI Inside" (2024) + Bessemer Vertical AI / AI Services Roadmap (2025)** — https://a16z.com/vertical-saas-now-with-ai-inside/ ; https://www.bvp.com/ ; commentary https://www.vccafe.com/vertical-ai-in-2026-the-good-the-bad-and-the-ugly/ · Sell against the headcount/services line, not the software line ($6 services per $1 software); Bessemer scores functional value, economic value, competitive dynamics, defensibility. **Stages: M, W, $.** Pull job postings and wage data for the role you would replace; price at a fraction of loaded cost.

25. **Elena Verna, "PMF Treadmill" (2025-26)** — https://gtmnow.com/product-market-fit-has-always-been-a-treadmill-but-it-just-got-way-faster/ ; https://tomtunguz.com/product-market-fit-not-static/ · In AI products, fit is re-earned roughly quarterly. **Stages: S, G.** Quarterly: diff new model releases against your feature set to find what just got commoditised.

26. **Jason Lemkin / SaaStr 2025-26** — https://lennysnewsletter.com/p/we-replaced-our-sales-team-with-20-ai-agents ; https://sites.libsyn.com/77527/saastr-835-ai-b2b-in-2026-find-the-tailwinds-or-get-left-behind-with-saastr-ceo-and-founder-jason-lemkin · Founder in every deal until ~20 closed; build revenue, don't depend on rounds. **Stages: G, $.** Agents for research and drafting, humans for every consequential customer touch.

27. **Nikita Bier, latent-demand / distribution-first** — https://www.lennysnewsletter.com/p/how-to-consistently-go-viral-nikita-bier · Find latent demand and a channel before polish; killed 14 apps before TBH. Consumer-centric, lower weight here. **Stages: G, I.**

28. **Pieter Levels, 12 Startups in 12 Months** — https://levels.io/nomad-list-founder · Ship monthly, keep what gets paid for. A cadence discipline, not a validation method. **Stages: I, S.**

Lower priority for this goal but worth knowing: Steve Blank's Four Steps (customer discovery/validation loop), Bill Aulet's 24 Steps (beachhead + bottom-up TAM), Crossing the Chasm beachhead, Blue Ocean ERRC grid, Playing to Win cascade, Kevin Kelly 1000 True Fans (https://kk.org/thetechnium/1000-true-fans/), Indie Hackers revenue-verified case studies, Wizard-of-Oz / concierge / smoke tests (all catalogued in #6).

---

## 2. Recommended stack (in order) with go / kill gates

| # | Stage | Framework(s) | Go if | Kill if |
|---|---|---|---|---|
| 1 | Idea sourcing | PG annoyance log + Isenberg subreddit mining + YC RFS sub-problems + Walling step-1/2 filter | ≥10 candidate ideas with named communities | Idea only exists in your head |
| 2 | Business-design screen | Cohen "Ideal Bootstrapped" checklist + Tringas 5x rule | Recurring, B2B, $50-500/mo, naturally recurring pain, existing spend | One-off pain, consumer, no existing budget line |
| 3 | Tarpit & power screen | YC tarpit list + 7 Powers (counter-positioning / cornered resource) | You can state why incumbents and model vendors will not copy it | Ten dead lookalikes and no structural reason you differ |
| 4 | Problem scoring | Cohen "Is there a problem?" multiplicative score | Score ≥1 (indie threshold) | <1 after honest estimates |
| 5 | Market archetype | Sequoia Arc | Hair-on-Fire or quantified Hard Fact | Future Vision |
| 6 | ICP + wedge | Lenny ICP test + Kazanjy narrative ICP + Dixon wedge | 3-attribute ICP, 50 named accounts, 2 named expansion segments | Cannot name 50 real targets |
| 7 | Problem interviews | Mom Test, 10-15 interviews, log commitments | ≥5 give time/reputation (intros, follow-ups, data) | Only compliments |
| 8 | Pretotype demand test | Savoia xyz + fake door / landing page (from the Bland & Osterwalder menu) | Hits your pre-stated X% (e.g. 5% of targeted ICP visitors leave email) | Below threshold on real ICP traffic |
| 9 | Price discovery | Van Westendorp (band) then Gabor-Granger (point), 30+ ICP respondents, cross-checked against replaced labour cost | Band includes a price that clears unit economics at <30 customers | Acceptable price below cost-to-serve plus margin |
| 10 | Pre-sale | Kagan 3-in-48h, or 5 paid pilots / LOIs with deposits | 3+ paid before build | Everyone wants it free or "after launch" |
| 11 | Concierge / vibe-coded MVP | Core value loop only (one action, one payoff); founder-led delivery | Paying users use it weekly; Sean Ellis "very disappointed" ≥40% once n≥40 | Retention collapses after month 1 |
| 12 | Default-alive check + treadmill | PG default alive; Verna quarterly re-fit; Lemkin founder-in-every-deal | Revenue > costs by month 1-3 without funding | Needs capital to reach break-even |

Pipeline stages `frame` → `risks` cover rows 1-6 and 9 as desk work and *prepare* rows 7-12; rows 7-12 only count as evidence when real humans and real money are involved.

---

## 3. Anti-patterns and tarpits

- **Classic YC tarpits**: social network for X, discovery apps for restaurants/events/music, friend-finding, consumer travel planning, generic note-taking (Caldwell/Seibel; Rickard's list).
- **AI-era tarpits** (HN thread https://news.ycombinator.com/item?id=47995879): chat-with-your-docs, generic copilots, multi-model chat aggregators, AI ad/copy generators, AI cold outbound, "AI analytics dashboard", legal/medical advice bots, anything whose whole value is one prompt a model vendor can ship natively. Cursor shows a "wrapper" can win, but only with workflow ownership and proprietary correction data.
- **Seat pricing for agentic products**: buyers increasingly want per-outcome pricing (secondary commentary).
- **Future-Vision ideas while bootstrapped**: early enthusiasm is a weak signal there (Sequoia).
- **One-off pain, no budget line, no recurring need** (Cohen); **"people who use Excel" ICPs** (Lenny); **interest counted as demand** (one 2026 founder saw 23 "interested" become 2 signups: https://hackernoon.com/i-spent-30-days-vibe-coding-an-mvp-burned-$127-broke-everything-and-still-found-product-market).
- **Hiring or spending ahead of revenue** (PG default-dead; Lemkin "seed as allowance").
- **Narrowing so far there is no next segment** (wedge test: name the two segments after this one).

---

## 4. LLM-synthetic research: pitfalls and how we triangulate

Evidence (2025-26):
- Synthetic panels show five systematic distortions: stereotyping, insufficient individuation, representation bias, ideological bias, hyper-rationality; individual-level correlation with real respondents only ~0.20 even with 500+ prior answers per persona; regressions on synthetic data had ~48% coefficient divergence and ~32% sign flips vs real survey data. https://arxiv.org/pdf/2609.13148
- LLM personas skew younger, more educated, more Western, more liberal; the skew grows the more the persona itself is LLM-generated (same paper).
- Detailed personas can perform *worse* than minimal census-style ones (Columbia/NeurIPS 2025, reported second-hand): https://kromatic.com/blog/synthetic-personas-customer-discovery/
- 81-article scoping review: persona generation is rarely validated against real humans. https://arxiv.org/pdf/2504.04927
- NN/g (per secondary source) finds synthetic data weakest for specialised audiences, i.e. exactly B2B niches: https://bigideasdb.com/synthetic-users-vs-real-customer-research (secondary; NN/g origin not verified).
- Vendor "AI validators" mostly rank themselves first; useful only as live-source aggregators, never as a verdict. https://kinda.ai/blog/ai-market-research-tools-comparison-dont-let-ai-lie-to-you

How this pipeline uses LLMs safely:
1. **Divergence, not verdicts**: hypothesis generation, question guides, canvas drafts, competitor matrices, clustering real transcripts. Gates are computed in code from labelled evidence, and `wtp`/`economics` cannot pass on STATED evidence alone.
2. **Never for**: WTP estimates, demand sizing as fact, or substitute interviews. Optimism bias produces false positives.
3. **Ground personas in real data**: the `icp` prompt forbids invented inner life and marks traits OBSERVED vs INFERRED (PDLC Empathy & Personas rules).
4. **Label synthetic output** and keep it out of the go/kill table; only stack rows 7-11 (real humans, real money) count as validation.
5. **Triangulate every claim against ≥3 hard signals**: search volume/trend, job postings for the role/pain, forum complaint volume with distinct authors, competitor pricing pages and changelogs (Wayback for history), G2/Capterra 1-3 star reviews, and finally pre-sales or paid pilots. If Gemini says "strong demand" and fewer than two agree, treat it as no signal. The evidence ledger's `independence_group` and triangulation label exist for this.
6. **Deep research is fine for the desk layer**, but open the citations; several "80% of wrappers die" statistics circulating in 2026 have no primary report behind them.
