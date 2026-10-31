# 0004 - Flexible business-model objectives and thesis integrity

**Status:** accepted
**Date:** 2026-10-31
**Spec:** pipeline/objectives.py, pipeline/prompts/_common.md, docs/WORKFLOW.md §1b
**Deciders:** founder (Ali), Claude Code

## Context

An external multi-model review of a real run (a real run) showed the validator had a structural bias:
it silently re-scoped the thesis stage by stage until it was validating "what can be sold for $500 in
two weeks" instead of the founder's actual idea; it scored every idea as a direct SMB-sales motion, so
low per-user willingness-to-pay killed a PLG/directory model whose economics rest on a small paying
fraction of a large free base; it optimised only for immediate behavioural WTP (which always favours a
service); and it raised a KILL-level legal blocker from a single low-authority source while an entire
incumbent industry did the same thing legally. The gates and prompts were rigid where the business
needed to be flexible.

## Decision

- Add two brief inputs: `business_model` and `success_definition`. The latter resolves to an
  **objective** (`pipeline/objectives.py`): services_cash, compounding_product, plg_network,
  venture_scale, or default.
- Objectives carry per-stage **criticality demotions**: for compounding/PLG theses the immediate-WTP
  and break-even criteria stop being hard-KILL and cap at PIVOT. `gates.evaluate` reads the objective
  off the stage output (no new parameter) and computes an effective critical set. Kill flags still bite.
- Inject the business model, objective guidance and three integrity rules into every stage prompt via
  the common block: evaluate against the stated model (funnel sizing for PLG, not outbound); never
  silently re-scope the thesis; classify competitors substitute/complement/adjacent; run a
  disconfirmation + source-grading check before any KILL-level blocker.
- `frame` classifies the model and writes a **Thesis spine** (core mechanism, moat/end-state,
  non-negotiables). `risks` must test the core mechanism first and keep a test alive for the
  un-narrowed thesis. `decision` reports **scope_drift** and preserves the original option.

## Consequences

- The same idea can now pass as a PLG/compounding bet and fail as a direct-sales bet, which is correct.
- Gates no longer hard-KILL a directory/network thesis on immediate per-user WTP; they route it to the
  right experiment (claim-rate, activation) instead.
- Desk research still cannot validate; the objective only changes which risk is attacked first.
- Backward compatible: a brief with no success_definition behaves exactly as before (default objective).

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Leave gates fixed, fix only prompts | Less code | Model scores still feed a one-size gate; hard-KILLs persist | Doesn't fix the structural bias |
| One new "PLG mode" flag | Simple | Too coarse; services vs venture vs compounding differ | Needs a small objective taxonomy |
| Let the model choose the objective freely each stage | Flexible | Reintroduces drift; non-deterministic gates | Objective is pinned from the brief |

## Links

- Supersedes: N/A
- Related: 0001 (gates), 0003 (sounding board); the a real run run under runs/ that prompted this.
