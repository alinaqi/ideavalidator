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
| `get_status` | `run_id` | Progress + per-stage GO/PIVOT/KILL verdicts, plus `next_poll_seconds` (how long to wait before polling again). |
| `list_runs` | — | This Palgu account's runs — works in a new session. |
| `cancel_run` | `run_id` | Request cancellation of a running validation. |
| `get_report` | `run_id` | The decision memo once the run is done. |

Runs are persisted under `IV_STORE`, keyed to your **Palgu account**, so `get_status` / `get_report` /
`list_runs` keep working in a brand-new session (important for agents that span many turns).

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

- **Runs persist** to `IV_STORE` per Palgu account; the **key/sign-in cache is in-memory**, so after a
  restart a caller signs in again with `palgu_login` (their past runs are still there via `list_runs`).
- **No server-level OAuth** — the server is open; access to actually *run* a validation is gated by
  Palgu sign-in. Directory listing + OAuth is a follow-up.
- **No image generation** — report hero images need Palgu `/v1/images` (srooter#2070), not yet available.

---

# ideavalidator-web — Rust web app + hosted MCP (ADR 0013)

`web/` is a Rust service (axum + tokio) that adds a **web product** on top of the same Python engine: sign
in with Palgu, submit an idea, watch per-stage progress over SSE, read the GO/PIVOT/KILL memo, and see your
history. It **also** serves the same seven MCP tools at `/mcp`, so it is a drop-in replacement for the
Python `server/` above. It does **not** reimplement any scoring/stage logic — it spawns `worker/run_job.py`
(the unchanged engine) and streams its NDJSON. See **ADR 0013** (`docs/adr/0013-rust-web-app-and-mcp.md`).

Compared with the Python server it adds: persistent **accounts + run history in Postgres**, a browser
dashboard, live SSE progress, and the user's Palgu token **encrypted at rest** (AES-256-GCM). Sign-ins
survive new MCP sessions for history/reports; a brand-new MCP session still re-runs `palgu_login` once to
bind, then `list_runs` / `get_report` resolve across restarts.

## Environment variables

| Var | Required | Default | Purpose |
|-----|----------|---------|---------|
| `PORT` | no | `8000` | HTTP port the service binds (`0.0.0.0:$PORT`). |
| `DATABASE_URL` | **yes** | — | Postgres for `users` / `sessions` / `runs` / `run_stages`. Migrations run on startup. |
| `TOKEN_ENC_KEY` | **yes** | — | 32-byte key (base64 **or** hex) encrypting each user's Palgu token at rest. `openssl rand -hex 32`. Must decode to exactly 32 bytes. Never logged, never committed. |
| `PALGU_ORIGIN` | no | `https://api.palgu.ai` | Palgu origin for the device-code sign-in. |
| `IV_STORE` | no | `server_runs` | Disk dir for brief + stage output files (`<store>/<account>/<run>/<slug>/decision.md`). |
| `PYTHON_BIN` | no | `.venv/bin/python` | Interpreter used to spawn the worker. The Docker image sets `python3`. |
| `MAX_CONCURRENT_RUNS` | no | `3` | tokio-semaphore bound on concurrent validations. |
| `REQ_CHECK_TIMEOUT_MS` | no | `45000` | Hard deadline for one requirements check; past it the route answers 503. |
| `MAX_CONCURRENT_CHECKS` | no | `8` | Bound on concurrent requirements-check workers (separate from runs). |
| `PALGU_STRUCTURE_MODEL` | no | `gemini-3.8-flash` | Palgu model alias the worker uses for structured calls (same setting as the pipeline). |

Secrets come only from the environment; `.env` stays gitignored and `.env.example` lists every var with no
values.

## Requirements check API (ADR 0014)

`POST /api/v1/requirements/check` is the fast check the Palgu gateway runs on every spec (srooter#2785,
contract v1). It takes `Authorization: Bearer <Palgu key>`; the gateway sends a short-lived key scoped to
chat + research, and every LLM and research call runs on it. No sign-in or cookie is needed.

```bash
curl -X POST https://ideavalidator-web.onrender.com/api/v1/requirements/check \
  -H "Authorization: Bearer $PALGU_KEY" -H 'content-type: application/json' -d '{
  "intent": "A web app where freelance designers invoice clients and get paid by card.",
  "requirements": [{"id": "R-1", "text": "Store the full card number and CVV for one-click repeat payments."}],
  "context": {"project": "invoicer", "audience": "freelance designers", "existing_app": true},
  "depth": "quick"}'
# -> 200 {"verdict":"blocked","findings":[{"req_id":"R-1","kind":"wrong","severity":"blocker",
#         "message":"...","suggested_text":"...","evidence":[]}],"summary":"...",
#         "model":"gemini-3.8-flash","duration_ms":13189,"contract":1}
```

- `verdict`: `blocked` = at least one blocker (`wrong`, `contradiction`); `questions` = majors (`unclear`,
  `untestable`); `ok` = only minors (`missing`, `scope_creep`, `off_icp`, `unsupported_claim`) or none.
- Grounded research (with cited `evidence`) runs only when `context.existing_app` is `false`.
- Errors: 401 missing/rejected key, 402 Palgu's body passed through, 422 invalid body, 503 timeout or check
  failure. It never answers `ok` for a check that did not run.
- Only `depth: "quick"` is accepted. Logs carry counts only, never the key or the requirement text.

## Run locally

```bash
# 1. A local Postgres (reuses the test compose file).
docker compose -f web/docker-compose.test.yml up -d

# 2. Point the app at it, with a real 32-byte key.
export DATABASE_URL=postgres://iv:iv@localhost:5433/iv_test
export TOKEN_ENC_KEY=$(openssl rand -hex 32)
export PYTHON_BIN=.venv/bin/python     # the interpreter that can import pipeline/ + worker/

# 3. Run from the repo root (the worker is spawned relative to the CWD).
cargo run --manifest-path web/Cargo.toml --bin ideavalidator-web
# -> ideavalidator-web listening on http://0.0.0.0:8000
```

The binary applies the `web/migrations` schema on startup (embedded in the binary), so an empty database is
ready to use. Open `http://localhost:8000/` for the dashboard; the MCP connector URL is
`http://localhost:8000/mcp`.

## Tests

The required gate needs no database or Docker:

```bash
cd web && cargo test && cargo clippy --all-targets -- -D warnings && cargo fmt --check
```

The one DB-touching test is `#[ignore]`d and gated on `TEST_DATABASE_URL`:

```bash
docker compose -f web/docker-compose.test.yml up -d
TEST_DATABASE_URL=postgres://iv:iv@localhost:5433/iv_test \
  cargo test --manifest-path web/Cargo.toml -- --ignored
```

## Deploy (Render)

`render.yaml` defines `ideavalidator-web` (Docker, `web/Dockerfile`, build context = repo root), a managed
Postgres (`ideavalidator-db`) wired to `DATABASE_URL`, a 1 GB disk at `/data` for `IV_STORE`, and the env
vars above (`TOKEN_ENC_KEY` via `generateValue` — verify Render's value decodes to 32 bytes, else set one
with `openssl rand -hex 32`). The existing `ideavalidator-mcp` Python service stays in the blueprint so both
run side by side during the migration. The connector URL is `https://ideavalidator-web.onrender.com/mcp`.

Add it as a connector exactly as for the Python server (claude.ai / ChatGPT / Grok → paste the `/mcp` URL).

## Supersedes the Python server

Per ADR 0013, once the Rust `/mcp` is deployed and confirmed at parity, the Python `server/` is retired and
`mcp.json` is repointed at `ideavalidator-web`. Until then `server/` is kept intact for deploy parity.
