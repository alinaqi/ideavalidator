# 0010 - Anti-over-qualification (ICP-anchoring) and a self-validation layer

**Status:** accepted
**Date:** 2026-11-01
**Spec:** pipeline/prompts/_common.md, icp.md, classify.md, decision.md; pipeline/selfcheck.py,
pipeline/selfcheck_run.py; schemas classify/icp/decision

## Context

Validating phrok (a personal calling MCP) exposed a systemic failure: when the idea-as-stated looked
hard (consumer economics, commoditization), the pipeline quietly substituted a bigger, more defensible
business — healthcare infrastructure with HIPAA at $999/mo — and the gates rewarded it. The idea drifted
off its ICP into a regulated vertical the founder never named. This is goal-substitution /
over-qualification. Related failures seen the same session: a KILL resting on two fabricated (404)
competitor citations, and a `risks` gate scoring test_cheapness=0 while its own content listed
zero-cost tests.

## Decision

1. **Anti-over-qualification policy (prompts).** `_common.md` gains a rule: score the idea AS STATED,
   for its stated actor/ICP and business model; never swap in a different buyer, vertical, compliance
   regime or model to clear a gate; put any bigger/adjacent business in `adjacent_opportunities` as a
   SEPARATE idea that does not lift any score. `icp.md` tags each candidate `in_brief` and keeps the
   beachhead within the founder's ICP unless the brief invites a new vertical. `classify.md` and
   `decision.md` route "works better as X" into `adjacent_opportunities` and make the decision stage
   call out over-qualification explicitly. Schemas add `adjacent_opportunities` (classify/icp/decision)
   and `in_brief` (icp candidates); all optional, none scored.

2. **Self-validation layer (`pipeline/selfcheck.py`, deterministic + testable).** After a run it audits
   the pipeline's own output: `off_icp` (beachhead/vertical absent from the brief → over-qualification),
   `score_inconsistency` (e.g. gross_margin_below_50 flag vs gross_margin_pct>=50; test_cheapness<=1 with
   cheap tests listed), `weak_kill` (KILL on <2 strong-directness sources), `citation_unreachable`
   (sampled evidence URLs that 404, via an injected fetcher — tests make no network call). It writes
   `runs/<slug>/selfcheck.{md,json}`, runs automatically at the end of `run`, is available as a
   `selfcheck` CLI command, and is surfaced in the decision memo. Flags are **advisory** — they
   recommend verification/reruns; they never silently change a gate or auto-loop.

## Consequences

- The validator is anchored to the founder's idea and ICP; inflating into an adjacent business no longer
  reads as the idea passing.
- Every run ships with an automated audit of its own weak spots (over-qualification, inconsistency, weak
  KILLs, fabricated citations), making the output safer to trust and easy to re-run where flagged.
- Reachability flags only definitive 404/410 to avoid false positives on legitimate redirects.
