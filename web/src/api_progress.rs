//! Pure mapping from a stored [`Run`] + its [`RunStage`]s to the JSON status payload the API returns,
//! mirroring `server/tools.py::progress_payload` (fields: `run_id`, `slug`, `state`, `completed`,
//! `total`, `stages`, `next_poll_seconds`, `error`). Unit-tested without any HTTP.

use serde_json::{json, Value};

use crate::db::{Run, RunStage};

/// Total engine stages (`len(pipeline.stages.STAGES)`); locked here to match the Python contract.
pub const TOTAL_STAGES: usize = 10;

/// How long a client should wait before polling again, by run state (parity with the Python tool).
pub fn next_poll_seconds(state: &str) -> i64 {
    match state {
        "pending" => 20,
        "running" => 120,
        _ => 0,
    }
}

fn stage_json(s: &RunStage) -> Value {
    json!({ "stage": s.stage_id, "verdict": s.verdict, "score": s.score })
}

/// Build the status payload for a run and its recorded stages.
pub fn progress_payload(run: &Run, stages: &[RunStage]) -> Value {
    json!({
        "run_id": run.id,
        "slug": run.slug,
        "state": run.state,
        "completed": stages.len(),
        "total": TOTAL_STAGES,
        "stages": stages.iter().map(stage_json).collect::<Vec<_>>(),
        "next_poll_seconds": next_poll_seconds(&run.state),
        "error": run.error.clone().unwrap_or_default(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(state: &str) -> Run {
        Run {
            id: "r1".into(),
            account_id: "acc".into(),
            slug: "demo".into(),
            pitch: "p".into(),
            state: state.into(),
            error: None,
            created_at: 0,
        }
    }

    fn stage(id: &str) -> RunStage {
        RunStage {
            stage_id: id.into(),
            verdict: Some("GO".into()),
            score: Some(4.2),
            ts: 0,
        }
    }

    #[test]
    fn next_poll_matches_the_python_table() {
        assert_eq!(next_poll_seconds("pending"), 20);
        assert_eq!(next_poll_seconds("running"), 120);
        assert_eq!(next_poll_seconds("done"), 0);
        assert_eq!(next_poll_seconds("error"), 0);
    }

    #[test]
    fn payload_has_the_contract_fields_and_counts() {
        let stages = vec![stage("frame"), stage("market")];
        let p = progress_payload(&run("running"), &stages);
        assert_eq!(p["run_id"], "r1");
        assert_eq!(p["slug"], "demo");
        assert_eq!(p["state"], "running");
        assert_eq!(p["completed"], 2);
        assert_eq!(p["total"], 10);
        assert_eq!(p["next_poll_seconds"], 120);
        assert_eq!(p["stages"][0]["stage"], "frame");
        assert_eq!(p["stages"][1]["verdict"], "GO");
        assert_eq!(p["error"], "");
    }

    #[test]
    fn error_run_surfaces_the_message() {
        let mut r = run("error");
        r.error = Some("boom".into());
        let p = progress_payload(&r, &[]);
        assert_eq!(p["error"], "boom");
        assert_eq!(p["completed"], 0);
        assert_eq!(p["next_poll_seconds"], 0);
    }
}
