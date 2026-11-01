# Stage: SWOT / TOWS — {{title}}
PDLC state: {{pdlc_state}}. Stage question: {{stage_question}}
Date: {{today}}

{{common}}

## Idea brief
{{brief}}

## Prior stages
{{prior}}

## Your tasks for this stage
Build an **evidence-linked SWOT for the chosen beachhead**, then convert it into actions (TOWS).
Generic SWOT bullets are worthless; every item must cite a stage finding or a URL and carry a
confidence (HIGH/MED/LOW).
1. **Strengths**: founder/unfair advantages that matter *to this ICP* (audience, access, domain, data,
   speed, cost structure). Be honest if they are thin.
2. **Weaknesses**: missing distribution, missing trust/brand, feasibility gaps, single-founder
   capacity, no case studies, pricing power limits.
3. **Opportunities**: whitespace, trends, incumbent weaknesses from reviews, channel openings,
   regulatory changes.
4. **Threats**: incumbents bundling the feature for free, platform dependence (API/marketplace
   policy), substitutes, buyer budget cuts, AI commoditisation of the core function. Judge threats
   against the **category incumbents from the classify stage** (`category_classification` in Prior
   stages), and treat platform-bundling risk as **per-platform** (one host shipping it natively does not
   mean all do) — not a blanket kill. A load-bearing threat must cite a URL that actually loads; do not
   kill on a competitor you cannot verify.
5. **TOWS**: SO (use strengths to seize opportunities), WO (fix weaknesses by using opportunities),
   ST (use strengths to blunt threats), WT (defensive moves / what to avoid). 2-4 concrete actions each.
6. **Defensibility check** (Hamilton Helmer's 7 Powers): for each power — scale economies, network
   effects, counter-positioning, switching costs, branding, cornered resource, process power — say
   whether it plausibly applies within 12 months and why. Most bootstrapped businesses rely on
   counter-positioning, cornered resource (niche access) and switching costs; say which.

## Required sections
strengths, weaknesses, opportunities, threats, tows, defensibility

## Scoring criteria
strength_leverage (strengths are real and decisive for this ICP), weakness_manageability (weaknesses
can be mitigated without capital), opportunity_size (opportunities are concrete and near-term),
threat_tolerance (no single threat can end the business in year one).

## Kill flags for this stage
`incumbent_can_bundle_for_free_imminently`, `single_platform_dependency_with_hostile_policy`
