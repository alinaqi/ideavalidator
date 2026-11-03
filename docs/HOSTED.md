# Hosted ideavalidator — remote MCP server

Run ideavalidator as a **remote MCP server** so anyone can add it to claude.ai, ChatGPT or Grok with no
local setup. It's **bring-your-own-Palgu**: each user signs in to their own Palgu account inside the
session (`palgu_login`) and the pipeline runs on their key — they pay Palgu directly, you host no keys.

## Tools exposed

| Tool | Args | What it does |
|------|------|--------------|
| `palgu_login` | — | Returns a palgu.ai approve URL + code; polls in the background and stores your key for the session. |
| `palgu_status` | — | Whether this session is signed in, and on which plan. |
| `validate_idea` | `pitch` | Starts a validation from a one-sentence pitch; returns a `run_id`. |
| `get_status` | `run_id` | Progress + per-stage GO/PIVOT/KILL verdicts as they land. |
| `get_report` | `run_id` | The decision memo once the run is done. |

A full run is ten grounded stages (~20–40 min), so `validate_idea` is async: it returns a `run_id` you
poll with `get_status`, then read with `get_report`.

## Run locally

```bash
pip install -r requirements.txt -r requirements-server.txt
python -m server            # serves streamable HTTP on http://localhost:8000/mcp
```

## Deploy (Render)

The repo ships a `Dockerfile` and `render.yaml`. Create a Render Blueprint from the repo (or a Docker web
service pointing at the `Dockerfile`). Render sets `$PORT`; a 1 GB disk is mounted at `/data` (`IV_STORE`)
for per-session runs. The connector URL is `https://<service>.onrender.com/mcp`.

## Add it as a connector

- **claude.ai** → Settings → Connectors → *Add custom connector* → paste `https://<host>/mcp`.
- **ChatGPT** → enable Developer Mode / Connectors → add an MCP server → `https://<host>/mcp`.
- **Grok** → add an MCP server / integration → `https://<host>/mcp`.

Then, in any of them: run `palgu_login`, approve the code at palgu.ai, and ask it to `validate_idea`
with your pitch.

## v0.1 limitations (tracked)

- **Session state is in-memory** — a server restart drops sign-ins and the job list (runs on `/data`
  persist). Redis/Postgres persistence is a follow-up.
- **No server-level OAuth** — the server is open; access to actually *run* a validation is gated by
  Palgu sign-in. Directory listing + OAuth is a follow-up.
- **No image generation** — report hero images need Palgu `/v1/images` (srooter#2070), not yet available.
