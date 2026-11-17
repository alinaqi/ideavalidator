//! Job orchestration: [`JobManager`] turns a pitch (or an already-written brief) into a tracked run —
//! it inserts a `pending` row, registers a cancel token and spawns a semaphore-bounded background task
//! ([`crate::jobs_run`]) that runs the worker and folds progress into Postgres + the SSE hub. All side
//! effects go through the injected `AppState` traits, so the whole flow is unit-tested with an in-memory
//! DB and a fake spawner — no Postgres, no Python.

use std::path::{Path, PathBuf};

use rand::RngCore;

use crate::brief::write_brief;
use crate::db::{now_unix, Run, RunStage};
use crate::jobs_run::{guarded_run, SpawnCtx};
use crate::runs::CancelToken;
use crate::state::AppState;

pub use crate::jobs_run::run_worker;

/// A run whose brief is already on disk, ready to launch (pitch form writes one; url form ingests one).
pub struct BriefRef {
    pub slug: String,
    pub pitch: String,
    pub brief_path: PathBuf,
}

/// Orchestrates validation runs over the shared [`AppState`].
pub struct JobManager {
    st: AppState,
}

fn new_run_id() -> String {
    let mut bytes = [0u8; 6];
    rand::rngs::OsRng.fill_bytes(&mut bytes);
    hex::encode(bytes)
}

fn new_run(account_id: &str, run_id: &str, brief: &BriefRef) -> Run {
    Run {
        id: run_id.to_string(),
        account_id: account_id.to_string(),
        slug: brief.slug.clone(),
        pitch: brief.pitch.clone(),
        state: "pending".to_string(),
        error: None,
        created_at: now_unix(),
    }
}

impl JobManager {
    pub fn new(st: AppState) -> Self {
        JobManager { st }
    }

    fn run_dir(&self, account_id: &str, run_id: &str) -> PathBuf {
        Path::new(&self.st.config.store_dir)
            .join(account_id)
            .join(run_id)
    }

    async fn decrypt_token(&self, account_id: &str) -> Result<String, String> {
        let user = self
            .st
            .db
            .get_user(account_id)
            .await?
            .ok_or("not signed in")?;
        self.st.cipher.decrypt(&user.enc_token)
    }

    /// Start a validation run for `pitch`, returning its `run_id`. The worker runs in the background.
    pub async fn start_run(&self, account_id: &str, pitch: &str) -> Result<String, String> {
        let run_id = new_run_id();
        let out_dir = self.run_dir(account_id, &run_id);
        let (slug, brief_path) = write_brief(&out_dir, pitch)?;
        let brief = BriefRef {
            slug,
            pitch: pitch.to_string(),
            brief_path,
        };
        self.launch(account_id, &run_id, brief).await
    }

    /// Start a run from a brief already written to disk (used by the url/ingest form).
    pub async fn start_with_brief(
        &self,
        account_id: &str,
        brief: BriefRef,
    ) -> Result<String, String> {
        let run_id = new_run_id();
        self.launch(account_id, &run_id, brief).await
    }

    async fn launch(
        &self,
        account_id: &str,
        run_id: &str,
        brief: BriefRef,
    ) -> Result<String, String> {
        let token = self.decrypt_token(account_id).await?;
        self.st
            .db
            .insert_run(new_run(account_id, run_id, &brief))
            .await?;
        let cancel = CancelToken::new();
        self.st.runs.register(run_id, cancel.clone());
        let ctx = SpawnCtx {
            run_id: run_id.to_string(),
            brief_path: brief.brief_path,
            out_dir: self.run_dir(account_id, run_id),
            token,
            cancel,
        };
        tokio::spawn(guarded_run(self.st.clone(), ctx));
        Ok(run_id.to_string())
    }

    pub async fn get_run(&self, run_id: &str) -> Result<Option<Run>, String> {
        self.st.db.get_run(run_id).await
    }

    pub async fn list_runs(&self, account_id: &str) -> Result<Vec<Run>, String> {
        self.st.db.list_runs(account_id).await
    }

    pub async fn run_stages(&self, run_id: &str) -> Result<Vec<RunStage>, String> {
        self.st.db.run_stages(run_id).await
    }

    /// Request cancellation of a tracked run; returns whether it was being tracked.
    pub fn request_cancel(&self, run_id: &str) -> bool {
        self.st.runs.cancel(run_id)
    }
}

#[cfg(test)]
#[path = "jobs_tests.rs"]
mod tests;
