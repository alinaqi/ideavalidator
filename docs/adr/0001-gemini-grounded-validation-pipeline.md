# 0001 - Gemini-grounded, PDLC-gated validation pipeline

**Status:** accepted
**Date:** 2026-10-31
**Spec:** docs/WORKFLOW.md
**Deciders:** founder (Ali), Claude Code

## Context

We will validate a stream of business ideas and want each one judged the same way, with evidence we
can audit, under a "profitable from day one" constraint. We already have an operating model (Palgu
PDLC v5: states, four risk types, evidence-quality labels, experiment router/protocol, bet records) and
a Gemini API key. The risk with LLM research is confident fabrication and stated-intent evidence being
mistaken for demand.

## Decision

- A **stage pipeline** (`pipeline/`) with nine fixed stages mapped to PDLC states; each stage consumes
  prior-stage summaries, so order is enforced by declared dependencies.
- **Two-pass Gemini calls per stage:** (1) a search-grounded research pass (`google_search` tool) that
  returns prose plus grounding URLs; (2) a tools-free JSON-mode pass constrained by a per-stage JSON
  schema. Grounding and structured output are separated because combining them is unreliable and
  because the second pass is told to use only facts present in the notes.
- **Deterministic gates** (`gates.py`): GO/PIVOT/KILL computed from 0-5 criterion scores, kill flags
  and critical-criterion floors. The model proposes scores; code decides verdicts; humans override only
  in writing.
- **Evidence ledger** normalised with PDLC Evidence Quality labels (directness, behaviour vs stated,
  recency, source independence) and a triangulation summary per stage.
- Optional **Deep Research** mode via the Gemini Interactions API for broader stages.
- Python 3 + `google-genai`; secrets only in `.env`; outputs as JSON + Markdown in `runs/<slug>/`.

## Consequences

- Reproducible, comparable reports across ideas; evidence quality is visible, not implied.
- Desk research cannot pass a WTP or economics gate on stated evidence alone; the workflow forces a
  real-world pre-sale loop before any build decision.
- Cost: ~18 model calls per full pass; preview models may change names (configurable in `.env`).
- Limitation: Gemini's grounding returns redirect URLs; titles/domains are kept for independence
  grouping, but citations should be spot-checked before external use.

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Single mega-prompt per idea | Fast, cheap | No stage gates, no dependency order, unauditable | Violates P1/P4 of the workflow |
| Gemini CLI (`gemini`) instead of API | Already installed | Hard to constrain output, no schema enforcement, interactive | Not reproducible |
| Grounded call with `response_schema` in one pass | One call per stage | Grounding + JSON mode combination is unsupported/unstable on several models | Reliability |
| Let the model decide GO/PIVOT/KILL | Simpler | Verdict drifts with phrasing; no fixed floor for critical criteria | Gates must be deterministic |
| Claude as researcher | Strong reasoning | User asked for Gemini; Gemini has native Google Search grounding and Deep Research | Requirement |

## Links

- Supersedes: N/A
- Related: docs/WORKFLOW.md, docs/FRAMEWORKS.md, `palgu_pdlc_framework_2026_v5.xlsx`
