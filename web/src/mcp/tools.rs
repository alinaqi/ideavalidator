//! Pure response builders for the hosted MCP tools, byte-for-byte with `server/tools.py` so the Rust
//! `/mcp` reads identically to the retired Python server. No IO and no transport here — just strings and
//! the `tools/list` schema, all unit-tested against the Python wording.

use serde_json::{json, Value};

use crate::api_progress::TOTAL_STAGES;

/// Shown by every tool that needs a Palgu sign-in first. Matches `server/tools.py::NOT_SIGNED_IN`.
pub const NOT_SIGNED_IN: &str =
    "Not signed in to Palgu. Run the `palgu_login` tool first (approve the code at palgu.ai), \
then retry — the validation runs on your own Palgu key.";

/// One row of the `list_runs` table.
pub struct RunRow {
    pub run_id: String,
    pub state: String,
    pub completed: usize,
    pub slug: String,
}

/// `validate_idea` acknowledgement (parity with `server/tools.py::started_text`).
pub fn started_text(slug: &str, run_id: &str) -> String {
    format!(
        "Validation started for '{slug}'. run_id: {run_id}\n\
Poll get_status(run_id='{run_id}') about every 2 minutes; read get_report when \
state is 'done' (a full run takes ~20-40 min)."
    )
}

fn row_line(r: &RunRow) -> String {
    format!(
        "{}  {:<9} {}/{}  {}",
        r.run_id, r.state, r.completed, TOTAL_STAGES, r.slug
    )
}

/// `list_runs` text, newest-first rows or the empty message (parity with `list_text`).
pub fn list_text(rows: &[RunRow]) -> String {
    if rows.is_empty() {
        return "No runs yet.".to_string();
    }
    rows.iter().map(row_line).collect::<Vec<_>>().join("\n")
}

/// `cancel_run` text — depends only on whether the account owns the run (parity with `cancel_for`).
pub fn cancel_text(owned: bool) -> String {
    if owned {
        "Cancellation requested.".to_string()
    } else {
        "No such run_id.".to_string()
    }
}

/// `get_report` text while a run is not yet `done` (parity with `report_text`'s not-done branch).
pub fn report_pending_text(run_id: &str, state: &str, completed: usize) -> String {
    format!(
        "Run {run_id} is {state} ({completed}/{TOTAL_STAGES}). \
The report is available once state is 'done'."
    )
}

fn schema(prop: Option<&str>) -> Value {
    match prop {
        Some(p) => {
            json!({"type": "object", "properties": {p: {"type": "string"}}, "required": [p]})
        }
        None => json!({"type": "object", "properties": {}}),
    }
}

fn tool(name: &str, description: &str, prop: Option<&str>) -> Value {
    json!({"name": name, "description": description, "inputSchema": schema(prop)})
}

/// The `tools/list` payload: the seven tools exposed by the hosted MCP, matching `server/app.py`.
pub fn tool_specs() -> Value {
    json!([
        tool("palgu_login", "Sign in to your Palgu account (approve a code at palgu.ai). Required before validating.", None),
        tool("palgu_status", "Show whether this session is signed in to Palgu, and on which plan.", None),
        tool("validate_idea", "Start validating a business idea from a one-sentence pitch. Returns a run_id to poll (~20-40 min).", Some("pitch")),
        tool("get_status", "Progress of a run: state, completed/total stages, per-stage verdicts, and next_poll_seconds.", Some("run_id")),
        tool("list_runs", "List this Palgu account's validation runs (works across sessions).", None),
        tool("cancel_run", "Request cancellation of a running validation.", Some("run_id")),
        tool("get_report", "Get the GO/PIVOT/KILL decision memo for a completed run.", Some("run_id")),
    ])
}

#[cfg(test)]
#[path = "tools_tests.rs"]
mod tests;
