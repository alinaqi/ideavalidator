# 0012 - Hosted remote MCP server (install ideavalidator into claude.ai / ChatGPT / Grok)

**Status:** accepted
**Date:** 2026-11-03
**Spec:** server/ (keystore, jobs, runjob, palgu_session, briefs, tools, app), Dockerfile, render.yaml, docs/HOSTED.md

## Context

ideavalidator ships as a local Claude Code plugin that needs a venv, `install.sh` and a provider key.
To reach users on claude.ai, ChatGPT and Grok with no local setup, we want a hosted version. All three
hosts install the same thing today: a **remote MCP server** (streamable HTTP). So we build one server and
list it in each, rather than three native apps.

## Decision

- **One remote MCP server** (`server/app.py`) on the official `mcp` 2.x SDK (`MCPServer`,
  streamable-HTTP ASGI app at `/mcp`), reusing the existing `pipeline/` engine — no logic duplicated.
- **Bring-your-own-Palgu.** A caller runs `palgu_login` (our device-code flow, reused from
  `pipeline.palgu*`), approves at palgu.ai, and the minted key is held per MCP session
  (`ctx.session_id`). The pipeline runs on that key via `config.Settings._palgu` + `make_client`, so the
  user pays Palgu directly and we host no keys and build no billing.
- **Async jobs.** A full run is ~20–40 min, so `validate_idea` starts a background thread and returns a
  `run_id`; `get_status` streams per-stage verdicts; `get_report` returns the memo. State is an in-memory
  `JobRegistry` + `KeyStore`; run outputs go to a per-session dir on a mounted disk (`IV_STORE`).
- **Thin, tested layering.** Pure, unit-tested modules (`keystore`, `jobs`, `runjob`, `palgu_session`,
  `briefs`, `tools`); `app.py`/`__main__.py` are transport/entrypoint only (smoke-tested).
- **Deploy on Render** via `Dockerfile` + `render.yaml` (same repo).

## Known limits (tracked, not hidden)

- In-memory session/job state — a restart drops sign-ins and the job list (disk runs persist).
  Redis/Postgres is a follow-up.
- No server-level OAuth / directory listing yet; the server is open and gated only by Palgu sign-in
  (you can't run a validation without your own key).
- No image generation (Palgu `/v1/images`, srooter#2070).

## Consequences

- ideavalidator becomes installable into claude.ai/ChatGPT/Grok as one connector URL, no local setup.
- The provider abstraction (ADR 0011) pays off: per-user keys slot straight into the hosted engine.
- CLI and hosted server share one engine; `mcp`/`uvicorn` stay in `requirements-server.txt` so the CLI
  and test suite don't depend on them.
