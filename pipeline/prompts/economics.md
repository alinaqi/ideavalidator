# Stage: DAY-ONE PROFITABILITY — {{title}}
PDLC state: {{pdlc_state}}. Stage question: {{stage_question}}
Date: {{today}}

{{common}}

## Idea brief
{{brief}}

## Prior stages
{{prior}}

## Your tasks for this stage
Build the **default-alive** model for a bootstrapped operator (Paul Graham default alive; Jason
Cohen's "Designing the Ideal Bootstrapped Business"; Rob Walling's stair-step). Every number is
SOURCED or ESTIMATE with arithmetic shown. Currency: use the brief's currency, else EUR.
1. **Monthly cost floor**: hosting, AI/API usage per customer, tools, payment fees, insurance/legal,
   founder minimum draw (use the brief's figure or state the assumption). Research actual provider
   prices (URLs).
2. **Unit economics**: price per customer per month (from WTP target), cost to serve per customer,
   gross margin %, CAC estimate for founder-led/organic channels (time-cost converted to money at the
   founder's hourly value, plus any tooling), CAC payback months, rough LTV with a sourced churn
   assumption for this category.
3. **Break-even**: customers needed to cover the floor; months to reach it given channel capacity;
   and the number needed to reach the founder's income target.
4. **Channel capacity**: for each founder-accessible channel from the market stage: weekly reach,
   plausible conversion (sourced benchmarks for the category), customers per month, hours per week.
5. **Day-one revenue plan**: how to get paid **before** building (pre-sales, paid pilot, productised
   service, concierge delivery, deposits) and what minimum deliverable earns the first invoice.
6. **Sensitivity**: pessimistic / base / optimistic for price, conversion, churn, cost-to-serve; which
   variable kills the model first.
7. **Default-alive check**: with the base case, is the business cash-flow positive by month 1-3
   without capital? If not, what single change (price, segment, delivery model) would make it so?

## Required sections
cost_floor_monthly, unit_economics, breakeven, channel_capacity, day_one_plan, sensitivity,
default_alive_check

## Scoring criteria
breakeven_reachability (break-even customer count is reachable through named channels within ~90
days), cac_payback (≤3 months for founder-led motion), gross_margin (≥70% after AI/API costs),
time_to_first_revenue (first paid customer plausible within 30 days via pre-sale/pilot),
founder_capacity_fit (model works within the founder's stated hours).

## Kill flags for this stage
`breakeven_requires_paid_acquisition`, `gross_margin_below_50`, `first_revenue_needs_full_build`
