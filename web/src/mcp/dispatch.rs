//! Async `tools/call` dispatch: route a tool name + args over the shared [`AppState`], reusing P1 auth,
//! P2 [`JobManager`] and the P4 report path — no engine logic is duplicated. Each arm returns a
//! `tools/call` result value; the parity strings come from [`crate::mcp::tools`]. Signed-in scoping
//! matches `server/handlers.py`: only `validate_idea` surfaces `NOT_SIGNED_IN`; the read tools simply
//! scope to the (possibly empty) account, so an unknown run reads as "No such run_id.".

use std::path::Path;

use serde_json::{json, Value};

use crate::api::owned_run;
use crate::api_progress::progress_payload;
use crate::brief::slug;
use crate::db::Run;
use crate::jobs::JobManager;
use crate::mcp::sessions::account_for;
use crate::mcp::tools::{
    cancel_text, list_text, report_pending_text, started_text, RunRow, NOT_SIGNED_IN,
};
use crate::mcp::{login, rpc, sessions};
use crate::state::AppState;

fn arg<'a>(args: &'a Value, key: &str) -> &'a str {
    args.get(key).and_then(Value::as_str).unwrap_or("")
}

/// Route one `tools/call` to its handler, returning the result content value.
pub async fn call_tool(st: &AppState, session_id: &str, name: &str, args: &Value) -> Value {
    match name {
        "palgu_login" => rpc::tool_text(&login::login(st, session_id).await),
        "palgu_status" => rpc::tool_text(&sessions::status(st, session_id).await),
        "validate_idea" => rpc::tool_text(&validate(st, session_id, args).await),
        "get_status" => get_status(st, session_id, args).await,
        "list_runs" => rpc::tool_text(&list_runs(st, session_id).await),
        "cancel_run" => rpc::tool_text(&cancel_run(st, session_id, args).await),
        "get_report" => rpc::tool_text(&get_report(st, session_id, args).await),
        other => rpc::tool_error(&format!("Unknown tool: {other}")),
    }
}

async fn validate(st: &AppState, session_id: &str, args: &Value) -> String {
    let Some(account) = account_for(st, session_id) else {
        return NOT_SIGNED_IN.to_string();
    };
    let pitch = arg(args, "pitch");
    match JobManager::new(st.clone()).start_run(&account, pitch).await {
        Ok(run_id) => started_text(&slug(pitch), &run_id),
        Err(e) => e,
    }
}

async fn get_status(st: &AppState, session_id: &str, args: &Value) -> Value {
    let account = account_for(st, session_id).unwrap_or_default();
    let run_id = arg(args, "run_id");
    match owned_run(st, &account, run_id).await {
        Ok(run) => {
            let stages = st.db.run_stages(run_id).await.unwrap_or_default();
            rpc::tool_json(progress_payload(&run, &stages))
        }
        Err(_) => rpc::tool_json(json!({"error": "No such run_id."})),
    }
}

async fn list_runs(st: &AppState, session_id: &str) -> String {
    let account = account_for(st, session_id).unwrap_or_default();
    let runs = st.db.list_runs(&account).await.unwrap_or_default();
    let mut rows = Vec::with_capacity(runs.len());
    for r in &runs {
        let completed = st.db.run_stages(&r.id).await.unwrap_or_default().len();
        rows.push(RunRow {
            run_id: r.id.clone(),
            state: r.state.clone(),
            completed,
            slug: r.slug.clone(),
        });
    }
    list_text(&rows)
}

async fn cancel_run(st: &AppState, session_id: &str, args: &Value) -> String {
    let account = account_for(st, session_id).unwrap_or_default();
    let run_id = arg(args, "run_id");
    match owned_run(st, &account, run_id).await {
        Ok(_) => {
            JobManager::new(st.clone()).request_cancel(run_id);
            cancel_text(true)
        }
        Err(_) => cancel_text(false),
    }
}

async fn get_report(st: &AppState, session_id: &str, args: &Value) -> String {
    let account = account_for(st, session_id).unwrap_or_default();
    let run_id = arg(args, "run_id");
    let run = match owned_run(st, &account, run_id).await {
        Ok(r) => r,
        Err(_) => return "No such run_id.".to_string(),
    };
    if run.state != "done" {
        let completed = st.db.run_stages(run_id).await.unwrap_or_default().len();
        return report_pending_text(run_id, &run.state, completed);
    }
    read_memo(st, &run)
}

fn read_memo(st: &AppState, run: &Run) -> String {
    let memo = Path::new(&st.config.store_dir)
        .join(&run.account_id)
        .join(&run.id)
        .join(&run.slug)
        .join("decision.md");
    // Parity note: Python server/tools.py regenerates the memo via cli_report when decision.md is
    // missing. Here a run only reaches state "done" after the decision stage writes decision.md, so
    // that fallback is unreachable; a missing file means a genuinely absent/corrupt run.
    std::fs::read_to_string(&memo)
        .unwrap_or_else(|_| "The decision memo is not available for this run.".to_string())
}

#[cfg(test)]
#[path = "dispatch_tests.rs"]
mod tests;
