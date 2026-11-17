//! JSON REST endpoints behind the [`CurrentAccount`] extractor (401 when unauthenticated). Bodies are
//! serde-validated by [`crate::api_input`], run status is mapped by [`crate::api_progress`], and the
//! decision memo is rendered by [`crate::report`]. Runs are always scoped to the caller's account, so a
//! run owned by someone else reads as 404. The SSE stream lives in [`crate::api_stream`].

use std::path::Path as FsPath;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::{Html, IntoResponse, Response};
use axum::Json;
use serde_json::{json, Value};

use crate::api_input::{RunInput, RunReq};
use crate::api_progress::progress_payload;
use crate::db::Run;
use crate::extract::CurrentAccount;
use crate::ingest::{ingest_and_start, UrlForm};
use crate::jobs::JobManager;
use crate::report::report_page;
use crate::state::AppState;

fn json_err(code: StatusCode, msg: &str) -> Response {
    (code, Json(json!({ "error": msg }))).into_response()
}

fn run_json(r: &Run) -> Value {
    json!({
        "run_id": r.id, "slug": r.slug, "state": r.state, "pitch": r.pitch,
        "created_at": r.created_at, "error": r.error.clone().unwrap_or_default(),
    })
}

/// Fetch a run and confirm the caller owns it; otherwise 404 (never leak another account's run).
pub(crate) async fn owned_run(
    st: &AppState,
    account: &str,
    run_id: &str,
) -> Result<Run, StatusCode> {
    match st.db.get_run(run_id).await {
        Ok(Some(r)) if r.account_id == account => Ok(r),
        Ok(_) => Err(StatusCode::NOT_FOUND),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

async fn start_input(st: &AppState, account: &str, input: RunInput) -> Result<String, String> {
    match input {
        RunInput::Pitch(pitch) => JobManager::new(st.clone()).start_run(account, &pitch).await,
        RunInput::Url { url, angle } => {
            ingest_and_start(
                st,
                account,
                UrlForm {
                    url: &url,
                    angle: &angle,
                },
            )
            .await
        }
    }
}

/// `POST /api/runs` — start a run from `{pitch}` or `{url, angle?}`; returns `{run_id}`.
pub async fn create_run(
    CurrentAccount(account): CurrentAccount,
    State(st): State<AppState>,
    Json(req): Json<RunReq>,
) -> Response {
    let input = match req.validate() {
        Ok(i) => i,
        Err(e) => return json_err(StatusCode::BAD_REQUEST, &e),
    };
    match start_input(&st, &account, input).await {
        Ok(run_id) => (StatusCode::CREATED, Json(json!({ "run_id": run_id }))).into_response(),
        Err(e) => json_err(StatusCode::BAD_GATEWAY, &e),
    }
}

/// `GET /api/runs` — the caller's runs, newest first.
pub async fn list_runs(
    CurrentAccount(account): CurrentAccount,
    State(st): State<AppState>,
) -> Response {
    match st.db.list_runs(&account).await {
        Ok(runs) => {
            Json(json!({ "runs": runs.iter().map(run_json).collect::<Vec<_>>() })).into_response()
        }
        Err(e) => json_err(StatusCode::INTERNAL_SERVER_ERROR, &e),
    }
}

/// `GET /api/runs/:id` — the progress payload (mirrors the hosted MCP `progress_payload`).
pub async fn run_status(
    CurrentAccount(account): CurrentAccount,
    State(st): State<AppState>,
    Path(id): Path<String>,
) -> Response {
    let run = match owned_run(&st, &account, &id).await {
        Ok(r) => r,
        Err(code) => return code.into_response(),
    };
    let stages = st.db.run_stages(&id).await.unwrap_or_default();
    Json(progress_payload(&run, &stages)).into_response()
}

/// `GET /api/runs/:id/report` — the decision memo rendered to a themed HTML page.
pub async fn run_report(
    CurrentAccount(account): CurrentAccount,
    State(st): State<AppState>,
    Path(id): Path<String>,
) -> Response {
    let run = match owned_run(&st, &account, &id).await {
        Ok(r) => r,
        Err(code) => return code.into_response(),
    };
    let memo = FsPath::new(&st.config.store_dir)
        .join(&account)
        .join(&id)
        .join(&run.slug)
        .join("decision.md");
    let md = std::fs::read_to_string(&memo)
        .unwrap_or_else(|_| format!("# Report not ready\n\nRun `{id}` is **{}**.", run.state));
    Html(report_page(&md)).into_response()
}
