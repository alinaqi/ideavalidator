# 0011 - Palgu single-key mode (sign up with Palgu instead of bringing your own keys)

**Status:** accepted
**Date:** 2026-11-02
**Spec:** pipeline/palgu.py, pipeline/palgu_run.py, pipeline/palgu_client.py, pipeline/config.py, cli.py

## Context

Running ideavalidator required the user to obtain a `GEMINI_API_KEY` (and, for the sounding board and
demand signals, several more keys). That is friction for new users. mixture-of-models solved the same
problem with Palgu's device-code sign-in: one `/palgu login` mints a per-device key and routes model
turns through Palgu's gateway. We want the same easy path here.

## Decision

- **Device sign-in** (`pipeline/palgu.py` pure + `pipeline/palgu_run.py` network), ported from
  mixture-of-models: `POST https://api.palgu.ai/auth/device/code` → approve at
  `https://www.palgu.ai/connect?code=…` → poll `POST /auth/token` → store the minted key in `.env` as
  `PALGU_API_KEY` (gitignored, mode 600). `GET /me` for `palgu status`. client_id = `ideavalidator`.
- **PalguClient** (`pipeline/palgu_client.py`) implements the same interface as GeminiClient over Palgu's
  OpenAI-compatible `/v1/chat/completions`: research/deep_research/research_urls are chat completions,
  structure uses `response_format: json_schema`, the model is pinned with `x-srooter-pin`. Built to the
  mixture-of-models-documented contract.
- **Provider selection** (`config.Settings.from_env` + `make_client`): an explicit `GEMINI_API_KEY` wins
  (full Google-Search grounding); otherwise a `PALGU_API_KEY` selects Palgu; otherwise `MissingKeyError`.
  The CLI (`_make_client`) uses `make_client`, so `run`/`council`/`ingest`/`signals` all honour it.
- **CLI**: `palgu login | status | upgrade`; `doctor` prints the active provider.

## Known limits (tracked, not hidden)

- **Grounded web search** (Gemini `google_search` / `url_context`) is Gemini-native; a plain
  OpenAI-compatible `/v1` call can't do it, so Palgu research is currently model-native (empty `sources`).
  Exposing grounded research through Palgu is requested in a `github.com/alinaqi/srooter` issue; until
  then, users who want full evidence quality set `GEMINI_API_KEY`.
- **Demand-signal data APIs** (DataForSEO/Reddit/Apify) are not model calls — Palgu does not proxy them;
  they remain optional separate keys and degrade gracefully.
- **Council on Palgu** (multi-model seats via `/v1` + pins) is a follow-up; the single-key core run works now.

## Consequences

- New users can `palgu login` and run the full nine-stage pipeline on one key, no manual key collection.
- The pipeline is now provider-pluggable behind `make_client`; adding another gateway later is localised.
