# Business Model Validation Workflow

**Version 1.0 · 2026-10-31 · Operating model: Palgu PDLC Framework 2026 v5 · Researcher: Gemini (search-grounded) · Orchestrator: Claude Code**

This is the procedure we follow for every new business idea. It produces, per idea, an evidence ledger,
nine graded stage reports and a decision memo (GO / PIVOT / KILL) in `runs/<slug>/`. The target is not
"a good idea" but a business that is **profitable from day one**: founder-led sales, no paid
acquisition before unit economics are proven, first invoice before the first big build.

---

## 1. Principles (non-negotiable)

| # | Principle | Source |
|---|-----------|--------|
| P1 | **Desk research is never validation.** Gemini output can at most justify GO *to real-world behavioural tests* (interviews, pre-sales, paid pilots). It never justifies GO *to build*. | PDLC Evidence Quality: directness, behaviour vs stated intent |
| P2 | **Behaviour beats stated intent.** Money paid, workarounds built, jobs posted, tools switched > "I would use this". Every evidence item is labelled so we can see which kind it is. | PDLC Evidence Quality, PD-C032 |
| P3 | **Opportunity before solution.** Stage 1 restates the idea as actor + job + context + current workaround. If it only exists as a feature, it goes back to framing. | PDLC Opportunity Discovery, PD-C004/PD-C011 |
| P4 | **Attack the riskiest, weakest-evidenced assumption first.** Value and viability (will they pay, can we reach them profitably) before usability and feasibility. | PDLC Assumption & Risk Map, PD-C021 |
| P5 | **Smallest credible test that can change the decision.** Pre-sale, LOI, concierge, fake door, story interview. Never "build it and see". | PDLC Experiment Router, PD-C025 |
| P6 | **Pre-register predictions.** Every experiment states the prediction and the kill signal before results exist. Invalid/ambiguous results are recorded as such, not spun. | PDLC Experiment Protocol, PD-C026/029 |
| P7 | **Keep contrary evidence and UNKNOWNs visible.** No averaging away, no confidence theatre. | PD-C034, Research Synthesis |
| P8 | **Killed ideas stay in memory** with reasons and revisit triggers so we do not re-test the same assumptions. | PDLC Product Memory, PD-C039 |
| P9 | **Profitable from day one** means: break-even customer count reachable through channels we already have, ≥70% gross margin after AI/API costs, first revenue from a pre-sale or paid pilot within ~30 days. | Economics gate |

---

## 1b. Flexibility: business model and success definition

The validator judges an idea against the *kind of business* it is, not a single template. Two inputs,
set in the brief frontmatter (or classified by the `frame` stage if blank), steer every stage:

- **business_model**: direct-sales SaaS, plg_freemium, directory_graph, marketplace_network, usage_api,
  services, or hybrid. A PLG/directory/network model is sized by its funnel (reachable base -> profiled
  -> claimed -> activated -> paid) and a small paying fraction of a large free base, NOT as an outbound
  per-customer sales motion. Low per-user willingness-to-pay does not kill such a model when the funnel
  and moat math hold.
- **success_definition** -> objective: `services_cash`, `compounding_product`, `plg_network`,
  `venture_scale`, or default. The objective reweights the gates: for compounding/PLG theses the
  immediate-WTP and break-even criteria are demoted from hard-KILL to at-most-PIVOT (see
  `pipeline/objectives.py`), because the right first test is the acquisition loop, not a two-week pre-sale.

Three integrity rules every stage now enforces (in `pipeline/prompts/_common.md`):
1. **No silent re-scoping.** The founder's one-sentence pitch and Thesis spine (core mechanism, moat/
   end-state, non-negotiables, written in `frame`) are fixed. A stage may narrow the beachhead but must
   say so, keep the original thesis alive as a tracked option, and flag loudly if a pivot discards the
   founder's stated assets or moat. Easiest-to-sell-this-fortnight is not the same as validated.
2. **Substitute vs complement.** Classify each alternative before scoring competition; a complement
   (e.g. a continuous signal that augments an audit) is not judged as if it must replace the incumbent.
3. **Disconfirmation before KILL.** Before a KILL-level legal/feasibility blocker, check for incumbents
   already doing it and grade the source; a KILL may not rest on one low-authority citation.

The `decision` stage reports **scope_drift**: how far the recommended bet moved from the thesis, whether
that was evidence-forced or convenient, and whether it discards a moat — with the un-narrowed thesis
preserved as its own option.

## 2. Roles and tools

| Role | Who / what | Responsibility |
|------|------------|----------------|
| Founder | you | Writes the idea brief, runs every real-world test (interviews, pre-sales), makes the GO/PIVOT/KILL call |
| Orchestrator | Claude Code in this repo | Runs the pipeline, challenges outputs, keeps the evidence ledger honest, drafts experiment protocols and outreach assets |
| Researcher | Gemini (`gemini-3.1-pro-preview` with Google Search grounding; `gemini-3.8-flash` for JSON structuring; Deep Research agent for `--deep` runs) | Desk research with citations; produces the stage reports |
| Sounding board | 6 framework-based personas on different models (OpenAI, Anthropic, Google, DeepSeek, Moonshot, xAI, Zhipu, Cerebras, Groq, MiniMax) + Red Team + Chair | Multi-perspective debate that enriches the idea and attacks the desk-research consensus; pattern from eduBITES soundingBoard |
| Operating model | Palgu PDLC v5 (`palgu_pdlc_framework_2026_v5.xlsx`) | States, risk types, evidence quality labels, experiment router/protocol, bet record, kill conditions |
| Frameworks | see `docs/FRAMEWORKS.md` | Lean Canvas, Mom Test, JTBD, Sequoia PMF (hair on fire), Crossing the Chasm beachhead, Disciplined Entrepreneurship segmentation, Dunford positioning, 7 Powers, Van Westendorp/Gabor-Granger, pretotyping, default-alive |

---

## 3. The stage map

Each stage = one Gemini research pass → structured JSON → deterministic gate → Markdown report.
Stages consume the summaries of the stages they depend on, so order matters.

| # | Stage id | Question it answers | PDLC state | Depends on | Gate criteria (0-5 each) | Kill flags |
|---|----------|---------------------|------------|------------|---------------------------|------------|
| 1 | `frame` | Is this a solution-independent opportunity for a specific actor? | S1 FRAME | — | actor_specificity*, job_clarity, solution_independence, why_now, why_us | no_specific_actor, tarpit_pattern, solution_in_search_of_problem, requires_outside_capital_by_design |
| 2 | `problem` | Does the problem exist, recur and already cost money/behaviour? | S1 FRAME | frame | problem_evidence*, frequency, severity, existing_spend*, urgency | no_public_evidence_of_problem, problem_already_solved_well_and_cheaply, vitamin_not_painkiller |
| 3 | `market` | What do buyers do today, who competes, how big is the *reachable* market, what is shifting? | S1-S2 | frame, problem | market_pull*, reachable_market_size, competitive_whitespace, trend_tailwind, regulatory_feasibility | market_too_small_for_profitability, dominant_free_incumbent, regulatory_blocker_for_small_operator, no_founder_accessible_channel |
| 4 | `icp` | Which narrow segment has the most urgent, best-funded, most reachable version of the problem? | S1-S3 | frame, problem, market | beachhead_clarity, pain_urgency, budget_authority*, reachability*, segment_homogeneity | no_reachable_segment, buyer_has_no_budget, segments_too_heterogeneous |
| 5 | `swot` | For the beachhead: strengths, weaknesses, opportunities, threats → TOWS actions, 7 Powers check | S2 EXPLORE | market, icp | strength_leverage, weakness_manageability, opportunity_size, threat_tolerance | incumbent_can_bundle_for_free_imminently, single_platform_dependency_with_hostile_policy |
| 6 | `wtp` | What do comparable buyers already pay, for which value metric, and how do we test it behaviourally? | S3 DE-RISK | problem, market, icp | price_comparables, value_metric_clarity, budget_exists*, behavioral_signal, margin_room* | no_budget_line, category_price_near_zero, cost_to_serve_exceeds_price |
| 7 | `economics` | How many customers at what price/CAC make this profitable from month one? | S3 DE-RISK (viability) | icp, wtp | breakeven_reachability*, cac_payback, gross_margin*, time_to_first_revenue, founder_capacity_fit | breakeven_requires_paid_acquisition, gross_margin_below_50, first_revenue_needs_full_build |
| 8 | `risks` | Which assumptions are important and weakly evidenced; what is the smallest test? | S3 DE-RISK | problem, market, icp, wtp, economics | value_risk_coverage, viability_risk_coverage, feasibility_risk_coverage, test_cheapness | core_value_assumption_already_invalidated, riskiest_assumption_untestable_without_full_build |
| 9 | `decision` | GO / PIVOT / KILL, bet record, kill condition, two-week real-world plan, positioning draft | S3→S4 / Bet Portfolio | all | evidence_strength*, profitability_confidence, focus_clarity, execution_readiness | any_prior_stage_kill_unresolved, no_path_to_first_revenue_within_60_days |

`*` = critical criterion: a score below 2 forces KILL for that stage regardless of the average.

**Why ICP comes before SWOT and WTP.** Willingness to pay and competitive position are only meaningful
for a specific buyer. Running SWOT on "the whole market" produces generic bullets; running WTP without a
beachhead produces a price range too wide to test. The request order (idea → market → SWOT → WTP → ICP)
is preserved in spirit: the `market` stage already does a first SWOT-like whitespace/threat scan, and
`icp` can be rerun after `wtp` if pricing evidence changes the beachhead.

**Sounding board (council).** A separate, optional step run with `python -m pipeline.cli council`.
It is not a gate; it feeds the `decision` stage (which reads `council.json` when present) and the
founder. Recommended moments: after `frame` (to enrich a thin idea before paying for research) and
after `risks` (to attack the consensus before the memo). See §6b.

---

## 4. Gate logic

Per stage, computed deterministically in `pipeline/gates.py` from the scores Gemini assigns using the
shared 0-5 rubric (0 no evidence / 1 weak stated / 2 stated + indirect / 3 mixed with ≥1 behavioural /
4 several independent behavioural / 5 fresh, triangulated, transactional):

1. Any **kill flag** → `KILL`.
2. Any **critical criterion < 2** → `KILL`.
3. Mean ≥ 3.5 and no criterion < 2 → `GO`.
4. Mean ≥ 2.5 (or a non-critical criterion < 2) → `PIVOT`.
5. Otherwise → `KILL`. Missing/unparseable scores → `UNKNOWN`.

Overall roll-up precedence: `KILL` > `UNKNOWN` > `PIVOT` > `GO`.

What the verdicts mean:

- **GO** = proceed to the two-week behavioural test plan (Section 7). Not "go build".
- **PIVOT** = the idea is alive but something specific must change (segment, price, delivery model, problem framing). The decision stage names which. Rerun affected stages after the pivot.
- **KILL** = stop; record the bet with reasons and a revisit trigger in `runs/<slug>/decision.md` and the kill log (Section 8).
- **UNKNOWN** = Gemini could not produce scorable evidence; rerun the stage (often with `--deep`) or do the research manually before deciding.

A human overrides a gate only in writing, in the decision memo, with the reason (PD-C035: decisions traceable to evidence *and acknowledged judgment*).

---

## 5. Evidence ledger rules

Every stage output carries an `evidence` array. Each item is normalised by `pipeline/evidence.py`:

| Field | Values | Meaning |
|-------|--------|---------|
| `claim` | text | One factual claim, scoped to a segment/geography |
| `source_url` | URL | Exact source; no URL = weak by default |
| `source_type` | forum, review, job_post, pricing_page, report, news, official_doc, competitor_site, search_data, academic, interview, sales_signal, other | Where it came from |
| `directness` | HIGH / MED / LOW / UNKNOWN | Does it observe the actual behaviour the assumption is about? |
| `behavior_vs_stated` | BEHAVIOR / STATED / MIXED / UNKNOWN | Did people act (pay, switch, build, hire) or only say? |
| `recency` | FRESH (<18 months) / STALE / UNKNOWN | Still current? |
| `independence_group` | domain/org | Used to detect "ten copies of the same source" |

Item score 0-8 = directness (0-3) + behaviour (0-3) + recency (0-2). Triangulation label per stage:
NONE (0 items) / WEAK (1 independent origin) / MEDIUM (2) / STRONG (≥3). A stage with a STRONG label
but only STATED items is still weak evidence: read the table, not the label.

Interview and pre-sale results from the real-world loop are added as `source_type: interview` /
`sales_signal` items with `behavior_vs_stated` set honestly (an interview is STATED unless it describes
past behaviour; a deposit is BEHAVIOR).

---

## 6. Stage procedures (what Gemini does, what the founder does)

### Stage 0 — Intake (human, 30-60 min)
Copy `ideas/_template.md` to `ideas/<slug>.md` and fill every section. Weak briefs produce weak
research: the actor, the current workaround, the why-us and the day-one cost floor are mandatory.
Also list the verticals you are *not* sure about; the ICP stage must consider at least two you did not think of.

### Stage 1 — Frame (S1)
Gemini: restates as a solution-independent opportunity, fills a Lean Canvas marked HYPOTHESIS/EVIDENCED,
extracts VALUE/USABILITY/FEASIBILITY/VIABILITY hypotheses, runs the tarpit check and lists the research
questions. Founder: read the tarpit check and the reframed opportunity; if the reframe surprises you,
fix the brief and rerun before spending more.

### Stage 2 — Problem validation (S1)
Gemini: hunts problem signals (verbatim language from forums/reviews), demand proxies (search terms,
communities, job posts, paid services, templates), status-quo cost, hair-on-fire classification,
contrary evidence, and drafts a Mom Test interview guide. Founder: **book 5-10 interviews with people
matching the actor this week** using the guide. Past behaviour only; no pitching.

### Stage 3 — Market understanding (S1-S2)
Gemini: alternatives/status-quo map with pricing URLs, market-pull evidence, bottom-up SAM and a
bootstrapped year-1 SOM with arithmetic, trends/technology frontier, regulation, founder-accessible
distribution channels, whitespace, learn-not-copy principles. Founder: sanity-check sizing inputs and
confirm you can actually reach the top two channels.

### Stage 4 — ICP and beachhead (S1-S3)
Gemini: 6-10 candidate verticals scored on pain urgency, budget authority, reachability, WTP
comparables, competition density, unfair advantage, cycle length; picks a beachhead and bowling-pin
sequence; writes a behavioural ICP profile with buyer/user/approver roles, trigger events,
disqualifiers and named watering holes; marks traits OBSERVED vs INFERRED. Founder: pick the beachhead
(override allowed, in writing) and **build a list of 50 named prospects** from the watering holes.

### Stage 5 — SWOT / TOWS (S2)
Gemini: evidence-linked SWOT for the beachhead, TOWS actions, 7 Powers defensibility check.
Founder: take the 2-3 SO/WO actions into the two-week plan; take WT items as things not to do.

### Stage 6 — Willingness to pay (S3)
Gemini: price comparables with URLs, budget line and approver, value-metric options, floor/target/
ceiling anchors, 1-3 tier packaging, Van Westendorp + Gabor-Granger questions, and a **pre-sale
experiment protocol**. Founder: **run the pre-sale** (deposit, LOI, paid pilot, or paid concierge) with
the 50-prospect list at the target price. This is the single most important step in the workflow.

### Stage 7 — Day-one economics (S3 viability)
Gemini: monthly cost floor with provider prices, unit economics, break-even customers and months,
channel capacity, how to get paid before building, sensitivity, default-alive verdict. Founder:
replace estimates with your real numbers (hourly value, cost floor, hours/week) and rerun if they differ materially.

### Stage 8 — Assumption and risk map (S3)
Gemini: 10-20 falsifiable assumptions with risk type, importance, evidence status, priority, router
method, cost, decision-if-false; a two-week experiment plan with pre-registered success/kill signals;
research-coverage gaps; explicit limits of desk research. Founder: this is your sprint backlog.

### Stage 6b — Sounding board (council), optional but recommended before the memo
Six personas, each anchored in named thinking frameworks and seated on a *different* model so they do
not share one set of priors, read the brief, every finished stage summary and the labelled evidence
ledger, then: (1) open with a framework-driven position and a GO/PIVOT/KILL vote, an "enrichment"
(the one change that most improves the idea from their lens) and a "verify" item; (2) debate, turn by
turn, each seeing the freshest rebuttals; (3) a Red Team seat builds the strongest case against the
consensus and attacks the evidence ledger itself; (4) a Chair synthesises consensus, real disagreements,
the Red Team verdict, an **enriched idea** (problem, ICP, offer, price, channel, wedge, each marked
EVIDENCED or HYPOTHESIS), pivot options, claims to verify and votes.

| Seat | Frameworks | Preferred models |
|------|------------|------------------|
| Bootstrapper | Cohen ideal bootstrapped business + "Is there a problem?", Walling stair-step, PG default alive | DeepSeek, Kimi, GLM |
| Customer Anthropologist | Mom Test, JTBD, Torres opportunity tree, PDLC behaviour-over-stated | Claude Sonnet/Opus, Gemini |
| Market Realist | Sequoia Arc, base rates / outside view, 7 Powers, Tringas 5x | GPT, Grok, GLM |
| Pricing & Positioning Strategist | Van Westendorp / Gabor-Granger, value metric, services-line pricing, Dunford | Gemini, GPT, MiniMax |
| Distribution Operator | Dixon wedge, Kazanjy founding sales, Isenberg community-first, channel arithmetic | Grok, Groq, Cerebras, Kimi |
| Premortem Skeptic | Premortem, Inversion, second-order thinking, tarpit lists | Claude Opus, GPT, DeepSeek |
| Red Team | argues against the consensus and the ledger | Claude Opus, GPT, DeepSeek |
| Chair | synthesis to `schemas/council.json` | Claude Opus, GPT, Gemini |

Personas live in `pipeline/personas.json`; any subset of provider keys works (seats fall back to
available models, a failed seat is reported, not fatal). Rules the board must follow: cite ledger
items, prefix anything new with HYPOTHESIS, never invent numbers; unanimity is a warning sign, not
confidence. Founder: read the **Disagreements** and **Claims to verify** sections first; add the
enrichments you accept to the brief under `## Evidence updates` and rerun the affected stages.

### Stage 9 — Decision memo (S3→S4)
Gemini: verdict with rationale citing strongest behavioural and strongest contrary evidence; PDLC bet
record with an observable, dated kill condition; pivot options; two-week plan; evidence ledger summary;
what-would-change-our-mind; Dunford positioning draft. Founder: decide, sign the memo (add a
"Founder decision" section), and start day one of the plan.

---

## 7. The real-world loop (weeks 1-2 after the desk pass)

Desk research ends with a bet record and a kill condition. The next two weeks are behavioural:

| Day | Action | Evidence produced | Protocol field |
|-----|--------|-------------------|----------------|
| 1-2 | Publish the offer (landing page or one-pager with target price), build the 50-prospect list | — | population, method |
| 2-7 | 10+ Mom Test interviews (past behaviour) + close with a commitment ask (deposit / LOI / paid pilot) | interview items (STATED unless past behaviour), sales_signal items (BEHAVIOR) | primary measure |
| 5-10 | Concierge/manual delivery to the first 1-3 payers; log hours (cost-to-serve reality check) | BEHAVIOR items, cost data | guardrails |
| 10-14 | Compare results to the pre-registered prediction; update evidence ledger; rerun `wtp`, `economics`, `risks`, `decision` with the new evidence appended to the brief | updated gates | result, learning, next decision |

Pre-registered example prediction (from the WTP stage): "At least 3 of 15 beachhead conversations commit
money (deposit ≥ €X or signed paid pilot) within 14 days at the target price." Kill signal: "< 2 of 15
commit, or every payer needs a materially different scope."

Continue / pivot / stop rules follow the PDLC Experiment Protocol: result values are
supported / mixed / invalidated / unknown / invalid, and an invalid run (wrong population, no real
price, leading questions) is not weak evidence; it is no evidence.

---

## 8. Artefacts and memory

```
ideas/<slug>.md                 intake brief (hypotheses; append "## Evidence updates" after each loop)
runs/<slug>/<stage>.json        structured output incl. evidence ledger, triangulation, gate
runs/<slug>/<stage>.md          human-readable stage report
runs/<slug>/council.json|.md    sounding-board transcript, debate, Red Team case and chair synthesis
runs/<slug>/decision.md         decision memo + bet record (append "## Founder decision")
docs/KILL_LOG.md                one line per killed/parked idea: date, reason, revisit trigger
docs/FRAMEWORKS.md              the framework stack and when each applies
```

Rerunning a stage overwrites its files; copy the previous run to `runs/<slug>/archive/` first if the
comparison matters (PD-C033: stale evidence must stay visible, not vanish).

---

## 9. Running it

```bash
# one-time
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # set GEMINI_API_KEY

# full desk pass (≈ 9 grounded calls + 9 structuring calls; 15-40 min; a few euros)
python -m pipeline.cli run --idea ideas/<slug>.md

# selected stages, in canonical order; dependencies must already exist in runs/<slug>/
python -m pipeline.cli run --idea ideas/<slug>.md --stages frame,problem

# halt at the first KILL instead of running the remaining stages
python -m pipeline.cli run --idea ideas/<slug>.md --stop-on-kill

# slower, broader research using Gemini Deep Research (minutes per stage)
python -m pipeline.cli run --idea ideas/<slug>.md --stages market,icp --deep

# sounding board: multi-model debate on the brief + all finished stages (5-10 min)
python -m pipeline.cli council --idea ideas/<slug>.md --rounds 1

# decision memo roll-up
python -m pipeline.cli report --idea <slug>
python -m pipeline.cli stages
```

Council keys: set `KEYS_FILE=/path/to/shared.env` in `.env` (any env file holding
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `MOONSHOT_API_KEY`, `XAI_API_KEY`,
`GLM_API_KEY`, `CEREBRAS_API_KEY`, `GROQ_API_KEY`, `MINIMAX_API_KEY`) or put the keys in `.env`
directly. Precedence is repo `.env`, then `KEYS_FILE`, then the shell environment, so a stale
`export ANTHROPIC_API_KEY` in your profile cannot override the file. `doctor` prints which council
models are callable.

Model routing: research passes use `GEMINI_MODEL` with Google Search grounding; structuring uses
`GEMINI_STRUCTURE_MODEL` in JSON mode against `pipeline/schemas/<stage>.json`; `--deep` uses the
Deep Research agent through the Interactions API and then structures its report the same way.

---

## 10. Anti-pattern checklist (read before accepting a GO)

- Request counts or "everyone I asked loved it" treated as demand (PV04).
- Easy-to-use prototype mistaken for value (PV05).
- One enthusiastic design partner universalised into a market (PV09).
- Top-down TAM from a press release used as reachable market.
- Price validated by asking "what would you pay?" instead of asking for money.
- Twenty interviews that changed no decision (PV17).
- A failed WTP test explained away instead of recorded as INVALIDATED (PV18).
- Building the product "as the experiment" when a concierge or pre-sale would answer the question.
- Tarpit patterns: consumer social, generic productivity, horizontal AI wrappers without data or
  distribution, marketplaces without a supply wedge, buyers without a budget line.
- Needing paid acquisition, a sales team or outside capital to reach break-even.

---

## 11. Change log

- 1.0 (2026-10-31): initial workflow; nine stages; gates; evidence ledger; real-world loop.
- 1.1 (2026-10-31): multi-model sounding board (council) with framework personas, debate, Red Team and chair synthesis; decision stage consumes it.
