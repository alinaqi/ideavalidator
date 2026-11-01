# 0008 - Demand signals (search volume + social validation) as an additive booster

**Status:** accepted
**Date:** 2026-11-01
**Spec:** pipeline/signals.py, pipeline/signals_sources.py, pipeline/signals_run.py, pipeline/gates.py
**Deciders:** Ali Shaheen, Claude

## Context

Validation so far relied on Gemini desk research and the sounding board. Two cheap, real-world demand
tests were missing: how an idea is actually *searched* (search volume) and whether people *discuss* the
problem on Reddit/X. The founder has DataForSEO (search volume) and Apify/xAI keys (social listening).

Key constraint from the founder: **signals are additive**. Their presence should earn extra confidence;
their absence must never count against an idea — genuinely new markets routinely have little search
volume or social chatter, and penalising that would reintroduce the goal-substitution bias ADR 0004
set out to remove.

The founder named a "Zernio" API for social signals. On reading its docs, Zernio is a social-media
**publishing/outreach** API (schedule posts, WhatsApp, DM replies, ad campaigns) with no topic-level
*listening* endpoint, so it does not fit demand discovery. It is parked for the GO-stage outreach kit.

## Decision

- **Sources** (`signals_sources.py`, all best-effort — a missing key or any error returns `[]`, never
  raises): DataForSEO Google-Ads search volume; Apify Reddit scraper; xAI Grok live X search. Keys are
  read via `providers.load_keys(root, SIGNAL_KEYS)` with the existing precedence (repo .env > external
  KEYS_FILE > process env). DataForSEO was verified live.
- **Scoring** (`signals.py`, pure/deterministic): search volume and social chatter each contribute up to
  +0.25, capped at a total **+0.5**. No signal → 0, never negative.
- **Application** (`gates.py`): the bonus is added to the *verdict* computation for `market`, `problem`
  and `decision` only; the reported score stays the measured mean, and a note records the bonus. Kill
  flags and the sub-2 critical floor are evaluated first, so a bonus can **never** rescue a KILL or lift
  a floored stage past PIVOT. With no bonus (the default), gate behaviour is byte-for-byte unchanged.
- **Flow** (`signals_run.py` + CLI): `run` gathers signals once up front (skippable with
  `--no-signals`), writes `runs/<slug>/signals.{json,md}`, and stamps the bonus + a summary onto the
  `RunContext`; the summary is injected into the market/problem/decision prompts so the model can weigh
  it as evidence. A standalone `signals` subcommand and a `doctor` line (configured sources) round it out.
- The memo (`report.build_memo`) shows a Demand-signals section when `signals.json` exists.

## Consequences

- Real external demand evidence now informs the verdict without ever punishing new-market ideas.
- Three new best-effort network dependencies; none can break a run. Tests block the network via an
  autouse fixture and stub responses explicitly.
- Zernio remains available (key stored in the gitignored KEYS_FILE) for a future outreach kit, not here.
