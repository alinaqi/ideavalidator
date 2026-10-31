# Stage: ASSUMPTION & RISK MAP — {{title}}
PDLC state: {{pdlc_state}}. Stage question: {{stage_question}}
Date: {{today}}

{{common}}

## Idea brief
{{brief}}

## Prior stages
{{prior}}

## Your tasks for this stage
Apply the PDLC Assumption & Risk Map and Experiment Router. Discovery effort goes to assumptions
that are **both important and weakly evidenced** (PD-C021). Choose the smallest credible method that
can change the decision; never default to building (PD-C025).
1. Consolidate **10-20 assumptions** from all prior stages. For each: id, statement (falsifiable),
   risk_type VALUE / USABILITY / FEASIBILITY / VIABILITY, importance H/M/L, evidence_status
   SUPPORTED / MIXED / INVALIDATED / UNKNOWN / UNTESTED (from the evidence ledgers so far),
   evidence_weakness H/M/L, priority (H importance + weak evidence first), test_method from the
   router (story interview, sales commitment test / pre-sale, landing/pricing test, fake door,
   concierge, Wizard of Oz, technical spike, benchmark/model eval, design-partner pilot), test_cost
   (hours and euros), decision_if_false.
2. **Two-week experiment plan**: day-by-day or week-by-week sequence of the top 4-6 tests, each with
   the assumption ids it attacks, the method, the pre-registered success signal and the kill signal
   (PDLC Experiment Protocol: prediction before result).
3. **Research coverage gaps** (PDLC Research Coverage): which actors have we not heard from at all —
   buyer vs user vs approver, non-adopters/churned, experts vs novices, geography — and how to recruit
   them cheaply.
4. Note explicitly which risks desk research structurally cannot reduce (usability, real WTP, real
   retention) so the founder does not mistake this report for validation.

## Required sections
assumptions, experiment_plan, research_coverage_gaps, limits_of_desk_research

## Scoring criteria
value_risk_coverage (top value assumptions have a cheap behavioural test planned),
viability_risk_coverage (pricing/margin/channel assumptions have tests), feasibility_risk_coverage
(technical unknowns have a spike or benchmark), test_cheapness (the plan costs < 2 founder-weeks and
< €500 before any build).

## Kill flags for this stage
`core_value_assumption_already_invalidated`, `riskiest_assumption_untestable_without_full_build`


## Flexibility addenda
- The top-priority assumption MUST be the thesis's core mechanism (e.g. the acquisition/claim loop or the graph/network effect), not an incidental price point. Design its cheapest real test.
- If a prior stage narrowed the idea, add a research-coverage gap for the ORIGINAL (un-narrowed) thesis and the cheapest test that would keep it alive or kill it.
