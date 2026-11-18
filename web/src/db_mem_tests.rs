//! Unit tests for [`crate::db_mem`]: user/session round-trips, expiry, and the run/run-stage
//! lifecycle against the in-memory fake.

use super::*;

fn run(id: &str, account: &str) -> Run {
    Run {
        id: id.into(),
        account_id: account.into(),
        slug: "demo".into(),
        pitch: "p".into(),
        state: "pending".into(),
        error: None,
        created_at: now_unix(),
    }
}

#[tokio::test]
async fn users_and_sessions_round_trip() {
    let db = InMemoryDb::new();
    let u = User {
        account_id: "acc".into(),
        email: "a@b.com".into(),
        plan: "pro".into(),
        enc_token: "enc".into(),
    };
    db.upsert_user(u.clone()).await.unwrap();
    assert_eq!(db.get_user("acc").await.unwrap(), Some(u));
    let s = Session {
        token: "t".into(),
        account_id: "acc".into(),
        expires_at: now_unix() + 60,
    };
    db.create_session(s).await.unwrap();
    assert_eq!(db.session_account("t").await.unwrap(), Some("acc".into()));
    db.delete_session("t").await.unwrap();
    assert_eq!(db.session_account("t").await.unwrap(), None);
}

#[tokio::test]
async fn expired_session_is_hidden() {
    let db = InMemoryDb::new();
    db.create_session(Session {
        token: "t".into(),
        account_id: "acc".into(),
        expires_at: now_unix() - 1,
    })
    .await
    .unwrap();
    assert_eq!(db.session_account("t").await.unwrap(), None);
}

#[tokio::test]
async fn run_lifecycle_state_and_stages() {
    let db = InMemoryDb::new();
    db.insert_run(run("r1", "acc")).await.unwrap();
    db.append_stage(
        "r1",
        RunStage {
            stage_id: "frame".into(),
            verdict: Some("GO".into()),
            score: Some(4.2),
            ts: now_unix(),
        },
    )
    .await
    .unwrap();
    db.update_run_state("r1", "done", None).await.unwrap();
    assert_eq!(db.get_run("r1").await.unwrap().unwrap().state, "done");
    assert_eq!(db.run_stages("r1").await.unwrap().len(), 1);
}

#[tokio::test]
async fn list_runs_scopes_to_account_newest_first() {
    let db = InMemoryDb::new();
    let mut a = run("old", "acc");
    a.created_at = 100;
    let mut b = run("new", "acc");
    b.created_at = 200;
    db.insert_run(a).await.unwrap();
    db.insert_run(b).await.unwrap();
    db.insert_run(run("other", "someone-else")).await.unwrap();
    let runs = db.list_runs("acc").await.unwrap();
    assert_eq!(
        runs.iter().map(|r| r.id.as_str()).collect::<Vec<_>>(),
        ["new", "old"]
    );
}
