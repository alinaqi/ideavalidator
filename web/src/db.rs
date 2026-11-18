//! Persistence boundary. The [`Db`] trait hides Postgres behind async methods so handlers depend on a
//! trait object (`Arc<dyn Db>`); [`InMemoryDb`](crate::db_mem::InMemoryDb) is the test fake, `PgDb`
//! (sibling module) the real impl. P2 adds the run/run-stage methods used by job orchestration.

use async_trait::async_trait;
use std::time::{SystemTime, UNIX_EPOCH};

pub use crate::db_mem::InMemoryDb;

/// A signed-in user. The Palgu token is stored only in its encrypted form (`enc_token`).
#[derive(Clone, Debug, PartialEq)]
pub struct User {
    pub account_id: String,
    pub email: String,
    pub plan: String,
    pub enc_token: String,
}

/// An opaque session bound to an account, expiring at a unix timestamp (seconds).
#[derive(Clone, Debug, PartialEq)]
pub struct Session {
    pub token: String,
    pub account_id: String,
    pub expires_at: i64,
}

/// A validation run owned by an account.
#[derive(Clone, Debug, PartialEq)]
pub struct Run {
    pub id: String,
    pub account_id: String,
    pub slug: String,
    pub pitch: String,
    pub state: String,
    pub error: Option<String>,
    pub created_at: i64,
}

/// One completed stage within a run (verdict/score come from the engine's gate).
#[derive(Clone, Debug, PartialEq)]
pub struct RunStage {
    pub stage_id: String,
    pub verdict: Option<String>,
    pub score: Option<f64>,
    pub ts: i64,
}

/// Current unix time in seconds.
pub fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

#[async_trait]
pub trait Db: Send + Sync {
    async fn upsert_user(&self, user: User) -> Result<(), String>;
    async fn get_user(&self, account_id: &str) -> Result<Option<User>, String>;
    async fn create_session(&self, session: Session) -> Result<(), String>;
    async fn session_account(&self, token: &str) -> Result<Option<String>, String>;
    async fn delete_session(&self, token: &str) -> Result<(), String>;

    async fn insert_run(&self, run: Run) -> Result<(), String>;
    async fn update_run_state(
        &self,
        run_id: &str,
        state: &str,
        error: Option<&str>,
    ) -> Result<(), String>;
    async fn append_stage(&self, run_id: &str, stage: RunStage) -> Result<(), String>;
    async fn list_runs(&self, account_id: &str) -> Result<Vec<Run>, String>;
    async fn get_run(&self, run_id: &str) -> Result<Option<Run>, String>;
    async fn run_stages(&self, run_id: &str) -> Result<Vec<RunStage>, String>;

    /// Delete an account and everything keyed to it (sessions, runs, run-stages, the user row).
    /// Returns how many runs were removed. Idempotent: a missing account deletes nothing.
    async fn delete_account(&self, account_id: &str) -> Result<u64, String>;
}
