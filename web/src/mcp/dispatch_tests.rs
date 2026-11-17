//! Tool-dispatch tests with an in-memory DB, a no-op worker spawner and a scripted Palgu — every tool's
//! response is checked against the Python-parity wording. No network, no Postgres, no Python.

use super::*;
use crate::db::{Run, RunStage, User};
use crate::mcp::sessions::map_session;
use crate::mcp::testsupport::{signing_in, state_with};

fn text_of(result: &Value) -> String {
    result["content"][0]["text"].as_str().unwrap().to_string()
}

async fn signed_in() -> AppState {
    let st = state_with(signing_in());
    let enc = st.cipher.encrypt("k-1").unwrap();
    st.db
        .upsert_user(User {
            account_id: "acc".into(),
            email: "a@b.com".into(),
            plan: "pro".into(),
            enc_token: enc,
        })
        .await
        .unwrap();
    map_session(&st, "sess", "acc");
    st
}

async fn seed_run(st: &AppState, id: &str, state: &str) {
    st.db
        .insert_run(Run {
            id: id.into(),
            account_id: "acc".into(),
            slug: "demo".into(),
            pitch: "p".into(),
            state: state.into(),
            error: None,
            created_at: 1,
        })
        .await
        .unwrap();
}

#[tokio::test]
async fn validate_idea_requires_sign_in() {
    let st = state_with(signing_in());
    let out = call_tool(&st, "anon", "validate_idea", &json!({"pitch": "x"})).await;
    assert_eq!(text_of(&out), NOT_SIGNED_IN);
}

#[tokio::test]
async fn validate_idea_starts_a_run_and_acknowledges() {
    let st = signed_in().await;
    let out = call_tool(
        &st,
        "sess",
        "validate_idea",
        &json!({"pitch": "an AI tutor"}),
    )
    .await;
    let text = text_of(&out);
    assert!(text.starts_with("Validation started for 'an-ai-tutor'. run_id: "));
    assert_eq!(st.db.list_runs("acc").await.unwrap().len(), 1);
}

#[tokio::test]
async fn get_status_reports_progress_and_unknown() {
    let st = signed_in().await;
    seed_run(&st, "r1", "running").await;
    st.db
        .append_stage(
            "r1",
            RunStage {
                stage_id: "frame".into(),
                verdict: Some("GO".into()),
                score: Some(4.0),
                ts: 1,
            },
        )
        .await
        .unwrap();
    let out = call_tool(&st, "sess", "get_status", &json!({"run_id": "r1"})).await;
    assert_eq!(out["structuredContent"]["total"], 10);
    assert_eq!(out["structuredContent"]["completed"], 1);
    assert_eq!(out["structuredContent"]["next_poll_seconds"], 120);

    let missing = call_tool(&st, "sess", "get_status", &json!({"run_id": "nope"})).await;
    assert_eq!(missing["structuredContent"]["error"], "No such run_id.");
}

#[tokio::test]
async fn list_runs_is_empty_then_tabulated() {
    let st = signed_in().await;
    assert_eq!(
        text_of(&call_tool(&st, "sess", "list_runs", &json!({})).await),
        "No runs yet."
    );
    seed_run(&st, "r1", "done").await;
    let out = text_of(&call_tool(&st, "sess", "list_runs", &json!({})).await);
    assert!(out.contains("r1  done"));
    assert!(out.contains("0/10  demo"));
}

#[tokio::test]
async fn cancel_run_depends_on_ownership() {
    let st = signed_in().await;
    seed_run(&st, "r1", "running").await;
    assert_eq!(
        text_of(&call_tool(&st, "sess", "cancel_run", &json!({"run_id": "r1"})).await),
        "Cancellation requested."
    );
    assert_eq!(
        text_of(&call_tool(&st, "sess", "cancel_run", &json!({"run_id": "nope"})).await),
        "No such run_id."
    );
}

#[tokio::test]
async fn get_report_is_not_ready_until_done() {
    let st = signed_in().await;
    seed_run(&st, "r1", "running").await;
    assert_eq!(
        text_of(&call_tool(&st, "sess", "get_report", &json!({"run_id": "r1"})).await),
        "Run r1 is running (0/10). The report is available once state is 'done'."
    );
    assert_eq!(
        text_of(&call_tool(&st, "sess", "get_report", &json!({"run_id": "nope"})).await),
        "No such run_id."
    );
}

#[tokio::test]
async fn unknown_tool_is_an_error_result() {
    let st = signed_in().await;
    let out = call_tool(&st, "sess", "frobnicate", &json!({})).await;
    assert_eq!(out["isError"], true);
    assert!(text_of(&out).contains("Unknown tool"));
}
