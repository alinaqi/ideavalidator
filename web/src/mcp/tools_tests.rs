//! Parity tests for the pure MCP tool text, locked against `server/tools.py`.

use super::*;

fn row(run_id: &str, state: &str, completed: usize, slug: &str) -> RunRow {
    RunRow {
        run_id: run_id.into(),
        state: state.into(),
        completed,
        slug: slug.into(),
    }
}

#[test]
fn not_signed_in_matches_python() {
    assert_eq!(
        NOT_SIGNED_IN,
        "Not signed in to Palgu. Run the `palgu_login` tool first (approve the code at palgu.ai), \
then retry — the validation runs on your own Palgu key."
    );
}

#[test]
fn started_text_names_slug_and_run_id() {
    let t = started_text("ai-tutor", "abc123");
    assert_eq!(
        t,
        "Validation started for 'ai-tutor'. run_id: abc123\n\
Poll get_status(run_id='abc123') about every 2 minutes; read get_report when \
state is 'done' (a full run takes ~20-40 min)."
    );
}

#[test]
fn list_text_is_empty_message_without_rows() {
    assert_eq!(list_text(&[]), "No runs yet.");
}

#[test]
fn list_text_pads_state_to_width_nine() {
    let rows = vec![
        row("r1", "done", 10, "demo"),
        row("r2", "running", 3, "beta"),
    ];
    let out = list_text(&rows);
    assert_eq!(out, "r1  done      10/10  demo\nr2  running   3/10  beta");
}

#[test]
fn cancel_text_depends_on_ownership() {
    assert_eq!(cancel_text(true), "Cancellation requested.");
    assert_eq!(cancel_text(false), "No such run_id.");
}

#[test]
fn report_pending_text_matches_python() {
    assert_eq!(
        report_pending_text("r9", "running", 4),
        "Run r9 is running (4/10). The report is available once state is 'done'."
    );
}

#[test]
fn tool_specs_lists_the_seven_tools_with_schemas() {
    let specs = tool_specs();
    let names: Vec<&str> = specs
        .as_array()
        .unwrap()
        .iter()
        .map(|t| t["name"].as_str().unwrap())
        .collect();
    assert_eq!(
        names,
        vec![
            "palgu_login",
            "palgu_status",
            "validate_idea",
            "get_status",
            "list_runs",
            "cancel_run",
            "get_report",
        ]
    );
    assert_eq!(specs[2]["inputSchema"]["required"][0], "pitch");
    assert_eq!(specs[0]["inputSchema"]["properties"], json!({}));
}
