# 0013 - Rust web app + hosted MCP over the Python engine (Palgu accounts)

**Status:** proposed
**Date:** 2026-11-17
**Supersedes:** 0012 (hosted remote MCP server) once the Rust `/mcp` reaches parity and `server/` is retired
**Spec:** web/ (Rust, axum/tokio), worker/run_job.py (NDJSON progress), Postgres schema, Dockerfile, render.yaml

## Context

0012 shipped a hosted **Python** MCP server (`server/`) that reuses the `pipeline/` engine: bring-your-own
Palgu, async jobs, per-account disk run store. It works, but it has no web UI, holds sign-ins in memory
(lost on restart), and has no persistent user/history store. We want ideavalidator usable as a **web
application** (sign in with Palgu, submit an idea, watch per-stage progress, read the GO/PIVOT/KILL memo,
see history) **and** keep a hosted MCP, with "high performance" as a stated goal.

The engine's wall-clock is ~20–40 min per run, **dominated by Palgu/Gemini API latency, not CPU**. So a
Rust rewrite of the pipeline would buy ~zero runtime speed while risking regressions in tested scoring
logic. The real concurrency/throughput wins from Rust are in the web/MCP transport, SSE streaming, auth
and job orchestration layer.

## Decision

- **Rust shell, Python engine reused.** A new Rust service (`web/`, axum + tokio) owns the dashboard,
  REST API, `/mcp`, Palgu auth, accounts/history and job orchestration. It does **not** re-implement any
  stage/prompt/gate logic. The tested `pipeline/` engine runs unchanged.
- **Engine runs as a spawned worker.** New thin entrypoint `worker/run_job.py` drives the engine one
  stage at a time and emits **NDJSON** to stdout (`{"event":"stage",...}`, then `done`/`cancelled`/
  `error`). Rust spawns it with `tokio::process`, reads stdout, updates Postgres and pushes Server-Sent
  Events. The only new Python is this worker; the engine is additive-only. A `tokio` semaphore bounds
  concurrent runs.
- **Persistent accounts + history in Postgres (sqlx).** `users`, `sessions`, `runs`, `run_stages`. Users
  are keyed by `account_id = sha256(palgu_email)[:16]`, **byte-identical to `server/store.py::account_id`**
  (locked by a cross-language test vector in `web/src/account.rs`), so existing hosted runs stay
  addressable. Stage output files stay on the `IV_STORE` disk.
- **Native Rust Palgu device-code auth.** Reimplement the RFC 8628 flow against `PALGU_ORIGIN`
  (`/auth/device/code`, `/auth/token`, `/me`). Web variant mints an httpOnly/Secure/SameSite session
  cookie. The user's Palgu token is **encrypted at rest** (AES-GCM, `TOKEN_ENC_KEY`), never logged, never
  placed in a client-exposed variable. The user still pays Palgu directly; we host no provider billing.
- **Frontend: server-rendered HTML + HTMX + SSE.** No Node build step. Live per-stage progress via SSE.
- **One service, incremental deploy on Render**, Postgres as a managed DB. The Rust `/mcp` reaches parity
  with the Python tools (`palgu_login`, `palgu_status`, `validate_idea`, `get_status`, `list_runs`,
  `cancel_run`, `get_report`), then `server/` is retired and `mcp.json` repointed.

## Phases

P0 scaffold + this ADR + `worker/run_job.py` (done) · P1 auth + Postgres users/sessions · P2 job
orchestration + SSE · P3 REST API + dashboard · P4 `/mcp` parity, retire `server/` · P5 Docker + render +
docs. Each phase is independently shippable and follows the repo's TDD and size gates.

## Alternatives considered

- **Full Rust port of the pipeline.** Rejected: weeks of work, high regression risk, ~0 runtime gain
  (LLM-bound), duplicates tested logic.
- **Keep Python MCP, add only a Rust web app.** Two services, duplicated auth/job code, two deploys.
  Rejected in favor of one Rust service owning both surfaces (user decision).
- **Rust calls the engine in-process via PyO3.** Rejected for P0: embedding CPython complicates the build
  and deploy for no benefit over a spawned worker; the subprocess boundary is simpler and isolates crashes.

## Known limits (tracked, not hidden)

- Palgu token lifetime/refresh not yet handled; an expired encrypted token forces re-sign-in (follow-up).
- In-flight run recovery after a deploy/restart is a follow-up (state is persisted; resume logic is not).
- Docker image carries both a Rust binary and the Python engine + venv; a split worker image is a later
  optimization.
- `ruff`/`mypy` are not currently installed in the repo venv; the worker is covered by pytest and the
  repo size/TDD gates, and lint/type-check wiring is a follow-up.

## Quality-gate exceptions (reviewed, deliberate)

The repo gates (`~/.claude/rules/quality-gates.md`) are met except for a few places where meeting them
literally would hurt the code; these were reviewed and kept on purpose:

- **Four data-layer files carry ~12 cohesive methods** (`db.rs` — the `Db` trait; `db_mem.rs` and
  `db_pg.rs` — its two impls; `jobs.rs` — `JobManager`). The ≤10-functions/file limit fights Rust's
  dyn-safe-trait model: a single `impl Db for T` block cannot be split across files, and carving the
  trait into `UserStore`/`RunStore` purely for the count adds indirection without separation-of-concerns
  value (run queries already live in `db_pg_runs.rs`). Every function in them is small; no file exceeds
  200 lines.
- **A few 4-argument dispatch/wrapper functions** (`mcp::dispatch::call_tool`, `mcp::http::tools_call`,
  `jobs_run::set_state`, `db_pg_runs::update_run_state`). In each, the "extra" argument is ambient
  context (`st`/`pool`/`session_id`) or the natural `(run_id, state, error)` shape mirrored from the
  `Db` trait; bundling them into a struct reads worse and, for `call_tool`, would churn 10 readable test
  call sites. Trait methods that show 4 args in tooling include `&self`, which is the receiver, not a
  parameter. The genuinely-improvable 4-arg functions were fixed (`new_run` now takes `&BriefRef`,
  `read_memo` takes `&Run`, `ingest_and_start` was decomposed).
- **`get_report` omits Python's `cli_report` regeneration fallback.** `server/tools.py` regenerates a memo
  when `decision.md` is missing; in this service a run only reaches state `done` after the decision stage
  writes `decision.md`, so that path is unreachable (noted in a code comment in `mcp/dispatch.rs`).

## Consequences

- ideavalidator gains a real web product (Palgu login, live progress, history) without touching the
  engine's scoring behavior.
- The provider abstraction (ADR 0011) and the per-account store (ADR 0012) carry straight over; 0012's
  server is superseded, not rewritten blindly.
- Cross-language `account_id` parity keeps one identity space across the CLI, the old Python server, and
  the new Rust service.
