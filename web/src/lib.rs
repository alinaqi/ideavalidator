//! ideavalidator web + MCP service.
//!
//! A thin Rust (axum/tokio) shell around the tested Python `pipeline/` engine: it owns the dashboard,
//! REST API, MCP endpoint, Palgu auth, accounts/history (Postgres) and job orchestration, while the
//! engine runs as a spawned worker (`worker/run_job.py`) that streams NDJSON progress. See
//! `docs/adr/0013-rust-web-app-and-mcp.md`.

pub mod account;
pub mod api;
pub mod api_input;
pub mod api_progress;
pub mod api_stream;
pub mod auth;
pub mod brief;
pub mod config;
pub mod crypto;
pub mod datefmt;
pub mod db;
pub mod db_mem;
pub mod db_pg;
pub mod db_pg_runs;
pub mod events;
pub mod extract;
pub mod ingest;
pub mod jobs;
pub mod jobs_run;
pub mod jobs_url;
pub mod mcp;
pub mod palgu;
pub mod palgu_flow;
pub mod palgu_http;
pub mod report;
pub mod reqcheck;
pub mod reqcheck_input;
pub mod reqcheck_proc;
pub mod router;
pub mod runs;
pub mod session;
pub mod sse;
pub mod state;
pub mod views;
pub mod worker_proc;
