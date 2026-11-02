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
  The device object sends all four fields the live contract requires: `name`, `platform`
  (darwin/win32/linux via `platform_tag`), `client_version` (`palgu.CLIENT_VERSION`) and a v4 UUID
  `install_id`.
- **PalguClient** (`pipeline/palgu_client.py`) implements the same interface as GeminiClient.
  research/deep_research/research_urls call Palgu's **grounded** `POST /v1/research` (`{"query": …}`,
  Bearer + `Idempotency-Key`), returning real `text` + `sources` (Google-Search citations) + `queries`
  (srooter#2063, live on prod). `structure` uses the OpenAI-compatible `/v1/chat/completions` with
  `response_format: json_schema`, pinned with `x-srooter-pin`. Human-readable sign-in strings live in
  `pipeline/palgu_text.py` (keeps `palgu.py` within the functions-per-file gate).
- **Provider selection** (`config.Settings.from_env` + `make_client`): a `PALGU_API_KEY` wins
  (single-key mode — grounded research and billing route through Palgu); otherwise an explicit
  `GEMINI_API_KEY` selects Gemini (bring-your-own-key); otherwise `MissingKeyError`. The CLI
  (`_make_client`) uses `make_client`, so `run`/`council`/`ingest`/`signals` all honour it.
- **CLI**: `palgu login | status | upgrade`; `doctor` prints the active provider.

## Known limits (tracked, not hidden)

- **Report hero images** (`/v1/images/generations`, srooter#2070) do not exist on Palgu yet, so HTML/PDF
  imagery stays Gemini-only; reports still render without images in Palgu mode.
- **Demand-signal data APIs** (DataForSEO/Reddit/Apify) are not model calls — Palgu does not proxy them;
  they remain optional separate keys and degrade gracefully.
- **Council on Palgu** (multi-model seats via `/v1` + pins) is a follow-up; the single-key core run works now.

## Update (2026-11-03)

srooter#2063 shipped (grounded `/v1/research` live on `api.palgu.ai`, verified on prod), closing the
original "grounded web search is Gemini-native, sources empty" limitation. Research through Palgu now
carries citations, so the provider default flipped to Palgu-wins. The device body gained the two
newly-required fields (`platform`, `client_version`). Only the images endpoint (#2070) remains Gemini-only.
A `402 Payment Required` from Palgu now surfaces a "top up at palgu.ai" message on stderr instead of
degrading silently, so an out-of-budget org can't be mistaken for "no evidence found".

## Consequences

- New users can `palgu login` and run the full nine-stage pipeline on one key, no manual key collection.
- The pipeline is now provider-pluggable behind `make_client`; adding another gateway later is localised.
