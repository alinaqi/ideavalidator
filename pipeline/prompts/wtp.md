# Stage: WILLINGNESS TO PAY — {{title}}
PDLC state: {{pdlc_state}}. Stage question: {{stage_question}}
Date: {{today}}

{{common}}

## Idea brief
{{brief}}

## Prior stages
{{prior}}

## Your tasks for this stage
Desk research cannot prove willingness to pay; only behaviour can (PDLC Market lens
"pricing/willingness-to-pay: behavioural > stated"; anti-pattern: asking "what would you pay?").
Your job is (a) to find every behavioural price signal that already exists and (b) to design the
cheapest real-world test the founder runs next.
1. **Price comparables**: what the ICP pays today for adjacent/competing tools and services — exact
   prices from pricing pages, per which value metric (seat, location, usage, outcome), with URLs.
   Include services/agencies/freelancer rates: they reveal the budget line.
2. **Budget source**: which existing budget line this would come from (software, marketing, staff
   time, compliance…) and who approves at this amount in the ICP.
3. **Value metric options**: 2-4 candidate metrics with pros/cons; which one scales with the
   customer's value and is easy to forecast for them.
4. **Price anchors**: floor / target / ceiling with rationale (10x rule: deliver ≥10x value vs price;
   also check against status-quo cost from the problem stage).
5. **Packaging hypotheses**: 1-3 tiers max for day one; what each includes; which tier we lead with.
6. **Van Westendorp question set** adapted to this ICP (4 questions) plus a Gabor-Granger ladder, for
   use in interviews — labelled STATED evidence.
7. **Pre-sale / commitment experiment** written as a PDLC Experiment Protocol: decision it informs,
   assumption, prediction (e.g. "3 of 10 ICP conversations pay a deposit / sign an LOI / pre-order at
   target price within 14 days"), population, method (pre-sale, paid pilot, LOI, deposit, concierge
   paid manually), primary measure, guardrails (no fake commitments, truthful claims), sample/stopping
   rule, decision rule (continue / pivot price / pivot segment / stop).
8. **Stated vs behavioural notes**: what in the evidence is merely stated and how much weight it got.

## Concrete willingness-to-pay estimate (required — show the math)
Produce a single concrete WTP figure (number or tight range) with an explicit derivation, not just a
range of comparables. Use a BLENDED heuristic and reconcile the three:
1. **Value-based:** WTP ≈ a defensible fraction (typically 10-30%) of the quantified value the customer
   gets per period — revenue unblocked, cost saved, or hours saved × their loaded hourly cost. State the
   value, the fraction and why.
2. **Comparable-anchored:** what this exact segment already pays for the nearest substitute (from the
   comparables above).
3. **10x rule sanity check:** the price must deliver ≥10x its cost in value; flag if it doesn't.
Show the arithmetic, label every input SOURCED or ESTIMATE, give a confidence (HIGH/MED/LOW), and state
plainly that this is a desk estimate to be proven by the pre-sale, never treated as validated demand.
Fill the `estimated_wtp` object {amount, period, method, basis, arithmetic, confidence}.

## Required sections
estimated_wtp,
price_comparables, budget_source, value_metric_options, price_anchors, packaging_hypotheses,
van_westendorp_questions, pre_sale_experiment, stated_vs_behavioral_notes

## Scoring criteria
price_comparables (ICP already pays comparable amounts for adjacent value), value_metric_clarity,
budget_exists (an owner and a budget line exist at this price), behavioral_signal (pre-orders,
waitlists, paid pilots, switching evidence found anywhere in the category), margin_room (target price
leaves ≥70% gross margin after cost-to-serve incl. AI/API costs).

## Kill flags for this stage
`no_budget_line`, `category_price_near_zero`, `cost_to_serve_exceeds_price`
