//! The run-driving half of job orchestration (split out of [`crate::jobs`] to keep each file small):
//! a background task acquires a concurrency permit, flips the run to `running`, spawns the worker, and
//! folds its NDJSON [`Event`]s into Postgres (`runs.state` + `run_stages`) while broadcasting to the SSE
//! hub. A stream that ends without a terminal event is treated as a cancel or an unexpected exit.

use std::path::PathBuf;

use crate::db::{now_unix, RunStage};
use crate::events::{parse_line, Event};
use crate::runs::CancelToken;
use crate::state::AppState;
use crate::worker_proc::{SpawnRequest, SpawnedWorker};

/// Everything a background task needs to run one worker.
pub(crate) struct SpawnCtx {
    pub run_id: String,
    pub brief_path: PathBuf,
    pub out_dir: PathBuf,
    pub token: String,
    pub cancel: CancelToken,
}

/// Background entrypoint: bound concurrency, run the worker, then clear the run's cancel token.
pub(crate) async fn guarded_run(st: AppState, ctx: SpawnCtx) {
    let _permit = st.sem.clone().acquire_owned().await.ok();
    let _ = st.db.update_run_state(&ctx.run_id, "running", None).await;
    let req = SpawnRequest {
        brief_path: ctx.brief_path,
        out_dir: ctx.out_dir,
        palgu_token: ctx.token,
        stages: "all".to_string(),
    };
    match st.spawner.spawn(req, ctx.cancel).await {
        Ok(worker) => run_worker(&st, &ctx.run_id, worker).await,
        Err(e) => {
            let _ = st.db.update_run_state(&ctx.run_id, "error", Some(&e)).await;
        }
    }
    st.runs.remove(&ctx.run_id);
}

/// Drive one worker's output to the store + hub. Returns when the stream ends.
pub async fn run_worker(st: &AppState, run_id: &str, mut worker: SpawnedWorker) {
    let mut terminal = false;
    while let Some(line) = worker.lines.recv().await {
        if let Some(event) = parse_line(&line) {
            terminal |= apply_event(st, run_id, &event).await;
            st.hub.publish(run_id, event);
        }
    }
    if !terminal {
        finalize_incomplete(st, run_id).await;
    }
}

fn to_stage(stage: &str, verdict: &Option<String>, score: Option<f64>) -> RunStage {
    RunStage {
        stage_id: stage.to_string(),
        verdict: verdict.clone(),
        score,
        ts: now_unix(),
    }
}

/// Apply one event to the store; returns `true` if it was a terminal event (state already set).
async fn apply_event(st: &AppState, run_id: &str, event: &Event) -> bool {
    match event {
        Event::Stage {
            stage,
            verdict,
            score,
        } => {
            let _ = st
                .db
                .append_stage(run_id, to_stage(stage, verdict, *score))
                .await;
            false
        }
        Event::Done => set_state(st, run_id, "done", None).await,
        Event::Cancelled => set_state(st, run_id, "cancelled", None).await,
        Event::Error { error } => set_state(st, run_id, "error", Some(error)).await,
        Event::Unknown => false,
    }
}

async fn set_state(st: &AppState, run_id: &str, state: &str, error: Option<&str>) -> bool {
    let _ = st.db.update_run_state(run_id, state, error).await;
    true
}

/// A stream that ended without a terminal event is a kill (cancel) or an unexpected exit.
async fn finalize_incomplete(st: &AppState, run_id: &str) {
    let cancelled = st.runs.is_cancelled(run_id);
    let state = if cancelled { "cancelled" } else { "error" };
    let error = (!cancelled).then_some("worker exited without completing");
    let _ = st.db.update_run_state(run_id, state, error).await;
}
