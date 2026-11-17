//! In-memory [`Db`] used across the test suite — no Postgres, no IO. Mirrors `PgDb`'s semantics closely
//! enough that the same orchestration/handler tests exercise real logic with a trivial fake.

use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Mutex;

use crate::db::{now_unix, Db, Run, RunStage, Session, User};

#[derive(Default)]
pub struct InMemoryDb {
    users: Mutex<HashMap<String, User>>,
    sessions: Mutex<HashMap<String, Session>>,
    runs: Mutex<HashMap<String, Run>>,
    stages: Mutex<HashMap<String, Vec<RunStage>>>,
}

impl InMemoryDb {
    pub fn new() -> Self {
        Self::default()
    }
}

#[async_trait]
impl Db for InMemoryDb {
    async fn upsert_user(&self, user: User) -> Result<(), String> {
        self.users
            .lock()
            .unwrap()
            .insert(user.account_id.clone(), user);
        Ok(())
    }

    async fn get_user(&self, account_id: &str) -> Result<Option<User>, String> {
        Ok(self.users.lock().unwrap().get(account_id).cloned())
    }

    async fn create_session(&self, session: Session) -> Result<(), String> {
        self.sessions
            .lock()
            .unwrap()
            .insert(session.token.clone(), session);
        Ok(())
    }

    async fn session_account(&self, token: &str) -> Result<Option<String>, String> {
        let session = self.sessions.lock().unwrap().get(token).cloned();
        Ok(session
            .filter(|s| s.expires_at > now_unix())
            .map(|s| s.account_id))
    }

    async fn delete_session(&self, token: &str) -> Result<(), String> {
        self.sessions.lock().unwrap().remove(token);
        Ok(())
    }

    async fn insert_run(&self, run: Run) -> Result<(), String> {
        self.runs.lock().unwrap().insert(run.id.clone(), run);
        Ok(())
    }

    async fn update_run_state(
        &self,
        run_id: &str,
        state: &str,
        error: Option<&str>,
    ) -> Result<(), String> {
        if let Some(run) = self.runs.lock().unwrap().get_mut(run_id) {
            run.state = state.to_string();
            run.error = error.map(str::to_string);
        }
        Ok(())
    }

    async fn append_stage(&self, run_id: &str, stage: RunStage) -> Result<(), String> {
        self.stages
            .lock()
            .unwrap()
            .entry(run_id.to_string())
            .or_default()
            .push(stage);
        Ok(())
    }

    async fn list_runs(&self, account_id: &str) -> Result<Vec<Run>, String> {
        let mut runs: Vec<Run> = self
            .runs
            .lock()
            .unwrap()
            .values()
            .filter(|r| r.account_id == account_id)
            .cloned()
            .collect();
        runs.sort_by_key(|r| std::cmp::Reverse(r.created_at));
        Ok(runs)
    }

    async fn get_run(&self, run_id: &str) -> Result<Option<Run>, String> {
        Ok(self.runs.lock().unwrap().get(run_id).cloned())
    }

    async fn run_stages(&self, run_id: &str) -> Result<Vec<RunStage>, String> {
        Ok(self
            .stages
            .lock()
            .unwrap()
            .get(run_id)
            .cloned()
            .unwrap_or_default())
    }
}

#[cfg(test)]
#[path = "db_mem_tests.rs"]
mod tests;
