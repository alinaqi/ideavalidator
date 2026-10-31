# 0003 - Multi-model sounding board for idea enrichment and dissent

**Status:** accepted
**Date:** 2026-10-31
**Spec:** docs/WORKFLOW.md §6b, pipeline/personas.json
**Deciders:** founder (Ali), Claude Code

## Context

Desk research from one model (Gemini) shares one set of priors. The founder asked for the
multi-perspective review pattern from eduBITES soundingBoard: personas on different models, a debate,
a Red Team seat and a synthesis, grounded in specific thinking frameworks, to enrich the idea and
surface dissent before the decision memo. Provider keys already exist in a shared env file (srooter).

## Decision

- `pipeline/providers.py`: one OpenAI-compatible chat client over a registry of ten providers
  (OpenAI, Anthropic, Google, DeepSeek, Moonshot, xAI, Zhipu, Cerebras, Groq, MiniMax). Keys resolve
  repo `.env` > external `KEYS_FILE` > process env (explicit config beats stale shell exports); only
  provider keys are read from the external file.
  stdlib `urllib` only; no `max_tokens` sent (provider-specific); failures isolated per seat.
- `pipeline/personas.json`: six personas defined by frameworks, not adjectives, each with a model
  preference list so that no two seats default to the same provider; plus Red Team and Chair seats.
- `pipeline/council.py` / `council_io.py`: dossier (brief + stage summaries + labelled evidence +
  unknowns) → parallel opening statements with a mandatory `Framework:` / `Vote:` / `Enrichment:` /
  `Verify:` footer → turn-based debate rounds (each member sees the freshest rebuttals) → Red Team →
  Chair synthesis structured by Gemini into `schemas/council.json`. Red Team and Chair fall back
  through their preference list, then any available model; a failed synthesis still writes the transcript.
- The council is **not a gate**. It writes `runs/<slug>/council.*`; the `decision` stage lists it as an
  optional input and reads its summary when present. Board output is labelled opinion/HYPOTHESIS unless
  it cites the ledger.

## Consequences

- Idea enrichment and dissent become a first-class, repeatable step; model diversity reduces shared
  blind spots (and the Red Team is told to treat unanimity as a warning).
- Cost: 6 + 6×rounds + 2 model calls per run; several minutes wall time; preview model ids rotate and
  are configurable in the registry.
- Risk: persuasive prose from many models can feel like evidence. Mitigated by the footer labels, the
  dossier's evidence labels, the Chair's EVIDENCED/HYPOTHESIS marking, and the rule that gates only
  move on ledger evidence.

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Call soundingBoard's API | Reuse a running product | Private, multi-tenant, needs its auth/credits | Must work standalone and be shareable |
| One model role-playing six personas | Cheapest | Same priors, same blind spots; the point is model diversity | Defeats the purpose |
| Make the council a gated stage | Uniform pipeline | Opinion would move verdicts | Violates P1 (evidence-only gates) |
| Route via a gateway (srooter) | One key | Extra infra for sharers | Optional later; registry supports a base-URL swap |

## Links

- Supersedes: N/A
- Related: 0001, 0002, github.com/eduBITES/soundingBoard (council_engine.py)
