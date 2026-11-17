//! Unit tests for [`crate::jobs`] — orchestration state transitions and cancellation driven by an
//! in-memory DB and a scripted fake spawner (no Postgres, no Python).

use super::*;
use std::sync::Arc;

use async_trait::async_trait;
use serde_json::Value;
use tokio::sync::Semaphore;

use crate::config::Config;
use crate::crypto::Cipher;
use crate::db::{InMemoryDb, User};
use crate::palgu::PalguHttp;
use crate::runs::RunRegistry;
use crate::sse::SseHub;
use crate::state::new_pending_map;
use crate::worker_proc::FakeSpawner;

const KEY_HEX: &str = "1111111111111111111111111111111111111111111111111111111111111111";

fn bref(slug: &str, pitch: &str) -> BriefRef {
    BriefRef {
        slug: slug.to_string(),
        pitch: pitch.to_string(),
        brief_path: std::path::PathBuf::new(),
    }
}

struct NullPalgu;

#[async_trait]
impl PalguHttp for NullPalgu {
    async fn post_json(&self, _path: &str, _body: Value) -> Result<Value, String> {
        Ok(Value::Null)
    }
    async fn get_json(&self, _path: &str, _bearer: &str) -> Result<Value, String> {
        Ok(Value::Null)
    }
}

fn stage_line(stage: &str) -> String {
    format!(r#"{{"event":"stage","stage":"{stage}","verdict":"GO","score":4.2}}"#)
}

fn fake(lines: Vec<String>, wait_cancel: bool) -> Arc<FakeSpawner> {
    Arc::new(FakeSpawner { lines, wait_cancel })
}

fn state_with(spawner: Arc<dyn crate::worker_proc::WorkerSpawner>) -> AppState {
    let cfg = Config::from(|k| match k {
        "TOKEN_ENC_KEY" => Some(KEY_HEX.to_string()),
        "IV_STORE" => Some(
            std::env::temp_dir()
                .join("iv-jobs-test")
                .to_string_lossy()
                .into(),
        ),
        _ => None,
    });
    AppState {
        db: Arc::new(InMemoryDb::new()),
        palgu: Arc::new(NullPalgu) as Arc<dyn PalguHttp>,
        cipher: Arc::new(Cipher::from_env_key(KEY_HEX).unwrap()),
        config: cfg,
        pending: new_pending_map(),
        spawner,
        hub: Arc::new(SseHub::new()),
        sem: Arc::new(Semaphore::new(2)),
        runs: RunRegistry::new(),
        mcp: crate::mcp::sessions::new_mcp_sessions(),
    }
}

async fn seed_user(st: &AppState) {
    let enc_token = st.cipher.encrypt("palgu-key").unwrap();
    let user = User {
        account_id: "acc".into(),
        email: "a@b.com".into(),
        plan: "pro".into(),
        enc_token,
    };
    st.db.upsert_user(user).await.unwrap();
}

#[tokio::test]
async fn run_worker_records_stages_then_done() {
    let st = state_with(fake(vec![], false));
    st.db
        .insert_run(new_run("acc", "r1", &bref("demo", "p")))
        .await
        .unwrap();
    let lines = vec![
        stage_line("frame"),
        stage_line("problem"),
        r#"{"event":"done"}"#.into(),
    ];
    let worker = FakeSpawner {
        lines,
        wait_cancel: false,
    }
    .spawn_for_test(CancelToken::new())
    .await;
    run_worker(&st, "r1", worker).await;
    assert_eq!(st.db.get_run("r1").await.unwrap().unwrap().state, "done");
    assert_eq!(st.db.run_stages("r1").await.unwrap().len(), 2);
}

#[tokio::test]
async fn run_worker_marks_cancelled_when_killed_mid_stream() {
    let st = state_with(fake(vec![], false));
    st.db
        .insert_run(new_run("acc", "r2", &bref("demo", "p")))
        .await
        .unwrap();
    let cancel = CancelToken::new();
    st.runs.register("r2", cancel.clone());
    cancel.cancel();
    let worker = FakeSpawner {
        lines: vec![stage_line("frame")],
        wait_cancel: true,
    }
    .spawn_for_test(cancel)
    .await;
    run_worker(&st, "r2", worker).await;
    assert_eq!(
        st.db.get_run("r2").await.unwrap().unwrap().state,
        "cancelled"
    );
    assert_eq!(st.db.run_stages("r2").await.unwrap().len(), 1);
}

#[tokio::test]
async fn start_run_requires_sign_in() {
    let jm = JobManager::new(state_with(fake(vec![], false)));
    assert!(jm.start_run("nobody", "a pitch").await.is_err());
}

#[tokio::test]
async fn start_run_inserts_a_run_and_cancel_tracks_it() {
    let st = state_with(fake(vec![stage_line("frame")], true));
    seed_user(&st).await;
    let jm = JobManager::new(st.clone());
    let run_id = jm.start_run("acc", "my great idea").await.unwrap();
    assert!(st.db.get_run(&run_id).await.unwrap().is_some());
    assert!(jm.request_cancel(&run_id));
    assert!(!jm.request_cancel("missing"));
}
