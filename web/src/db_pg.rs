//! Postgres-backed [`Db`] via sqlx RUNTIME queries (`sqlx::query(...).bind(...)`) — no compile-time
//! macros, so this builds with no live `DATABASE_URL` and no offline cache. Parameters are always bound,
//! never concatenated. Exercised by an env-gated `#[ignore]` integration test.

use async_trait::async_trait;
use sqlx::postgres::PgPoolOptions;
use sqlx::{PgPool, Row};

use crate::db::{now_unix, Db, Run, RunStage, Session, User};
use crate::db_pg_runs as runs;

const UPSERT_USER: &str = "INSERT INTO users (account_id, email, plan, enc_token, created_at) \
    VALUES ($1, $2, $3, $4, $5) ON CONFLICT (account_id) DO UPDATE \
    SET email = EXCLUDED.email, plan = EXCLUDED.plan, enc_token = EXCLUDED.enc_token";

pub struct PgDb {
    pool: PgPool,
}

impl PgDb {
    /// Open a pool. Call [`migrate`](Self::migrate) once after connecting.
    pub async fn connect(url: &str) -> Result<Self, String> {
        let pool = PgPoolOptions::new()
            .max_connections(5)
            .connect(url)
            .await
            .map_err(|e| e.to_string())?;
        Ok(PgDb { pool })
    }

    /// Apply the initial schema (idempotent; all tables use `IF NOT EXISTS`).
    pub async fn migrate(&self) -> Result<(), String> {
        sqlx::raw_sql(include_str!("../migrations/0001_init.sql"))
            .execute(&self.pool)
            .await
            .map_err(|e| e.to_string())?;
        Ok(())
    }
}

#[async_trait]
impl Db for PgDb {
    async fn upsert_user(&self, user: User) -> Result<(), String> {
        sqlx::query(UPSERT_USER)
            .bind(user.account_id)
            .bind(user.email)
            .bind(user.plan)
            .bind(user.enc_token)
            .bind(now_unix())
            .execute(&self.pool)
            .await
            .map(|_| ())
            .map_err(|e| e.to_string())
    }

    async fn get_user(&self, account_id: &str) -> Result<Option<User>, String> {
        let row = sqlx::query(
            "SELECT account_id, email, plan, enc_token FROM users WHERE account_id = $1",
        )
        .bind(account_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| e.to_string())?;
        Ok(row.map(|r| User {
            account_id: r.get("account_id"),
            email: r.get("email"),
            plan: r.get("plan"),
            enc_token: r.get("enc_token"),
        }))
    }

    async fn create_session(&self, session: Session) -> Result<(), String> {
        sqlx::query("INSERT INTO sessions (token, account_id, created_at, expires_at) VALUES ($1, $2, $3, $4)")
            .bind(session.token)
            .bind(session.account_id)
            .bind(now_unix())
            .bind(session.expires_at)
            .execute(&self.pool)
            .await
            .map(|_| ())
            .map_err(|e| e.to_string())
    }

    async fn session_account(&self, token: &str) -> Result<Option<String>, String> {
        let row =
            sqlx::query("SELECT account_id FROM sessions WHERE token = $1 AND expires_at > $2")
                .bind(token)
                .bind(now_unix())
                .fetch_optional(&self.pool)
                .await
                .map_err(|e| e.to_string())?;
        Ok(row.map(|r| r.get("account_id")))
    }

    async fn delete_session(&self, token: &str) -> Result<(), String> {
        sqlx::query("DELETE FROM sessions WHERE token = $1")
            .bind(token)
            .execute(&self.pool)
            .await
            .map(|_| ())
            .map_err(|e| e.to_string())
    }

    async fn insert_run(&self, run: Run) -> Result<(), String> {
        runs::insert_run(&self.pool, run).await
    }

    async fn update_run_state(
        &self,
        run_id: &str,
        state: &str,
        error: Option<&str>,
    ) -> Result<(), String> {
        runs::update_run_state(&self.pool, run_id, state, error).await
    }

    async fn append_stage(&self, run_id: &str, stage: RunStage) -> Result<(), String> {
        runs::append_stage(&self.pool, run_id, stage).await
    }

    async fn list_runs(&self, account_id: &str) -> Result<Vec<Run>, String> {
        runs::list_runs(&self.pool, account_id).await
    }

    async fn get_run(&self, run_id: &str) -> Result<Option<Run>, String> {
        runs::get_run(&self.pool, run_id).await
    }

    async fn run_stages(&self, run_id: &str) -> Result<Vec<RunStage>, String> {
        runs::run_stages(&self.pool, run_id).await
    }

    async fn delete_account(&self, account_id: &str) -> Result<u64, String> {
        runs::delete_account(&self.pool, account_id).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::now_unix;

    // Runs only with a real Postgres: `TEST_DATABASE_URL=... cargo test -- --ignored`.
    // See web/docker-compose.test.yml. The REQUIRED gate passes without it.
    #[tokio::test]
    #[ignore = "needs TEST_DATABASE_URL + Postgres"]
    async fn pg_round_trip() {
        let url = std::env::var("TEST_DATABASE_URL").expect("TEST_DATABASE_URL");
        let db = PgDb::connect(&url).await.unwrap();
        db.migrate().await.unwrap();
        let user = User {
            account_id: "acc1".into(),
            email: "a@b.com".into(),
            plan: "pro".into(),
            enc_token: "enc".into(),
        };
        db.upsert_user(user.clone()).await.unwrap();
        assert_eq!(db.get_user("acc1").await.unwrap(), Some(user));
        let s = Session {
            token: "tok".into(),
            account_id: "acc1".into(),
            expires_at: now_unix() + 60,
        };
        db.create_session(s).await.unwrap();
        assert_eq!(
            db.session_account("tok").await.unwrap(),
            Some("acc1".into())
        );
        db.delete_session("tok").await.unwrap();
        assert_eq!(db.session_account("tok").await.unwrap(), None);

        let run = Run {
            id: "run1".into(),
            account_id: "acc1".into(),
            slug: "demo".into(),
            pitch: "a pitch".into(),
            state: "pending".into(),
            error: None,
            created_at: now_unix(),
        };
        db.insert_run(run).await.unwrap();
        db.append_stage(
            "run1",
            RunStage {
                stage_id: "frame".into(),
                verdict: Some("GO".into()),
                score: Some(4.2),
                ts: now_unix(),
            },
        )
        .await
        .unwrap();
        db.update_run_state("run1", "done", None).await.unwrap();
        assert_eq!(db.get_run("run1").await.unwrap().unwrap().state, "done");
        assert_eq!(db.run_stages("run1").await.unwrap().len(), 1);
        assert_eq!(db.list_runs("acc1").await.unwrap().len(), 1);
    }
}
