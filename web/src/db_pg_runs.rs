//! Postgres run/run-stage queries, split out of `db_pg.rs` to keep each file small. All queries are
//! runtime `sqlx::query(...).bind(...)` — no compile-time macros, no offline cache, parameters always
//! bound. `PgDb`'s `Db` methods delegate here.

use sqlx::{PgPool, Row};

use crate::db::{now_unix, Run, RunStage};

const INSERT_RUN: &str =
    "INSERT INTO runs (id, account_id, slug, pitch, state, error, created_at) \
    VALUES ($1, $2, $3, $4, $5, $6, $7)";
const UPDATE_STATE: &str = "UPDATE runs SET state = $2, error = $3 WHERE id = $1";
const INSERT_STAGE: &str =
    "INSERT INTO run_stages (run_id, stage_id, verdict, score, ts) VALUES ($1, $2, $3, $4, $5)";
const SELECT_RUN: &str =
    "SELECT id, account_id, slug, pitch, state, error, created_at FROM runs WHERE id = $1";
const LIST_RUNS: &str = "SELECT id, account_id, slug, pitch, state, error, created_at FROM runs \
    WHERE account_id = $1 ORDER BY created_at DESC";
const SELECT_STAGES: &str =
    "SELECT stage_id, verdict, score, ts FROM run_stages WHERE run_id = $1 ORDER BY id";

fn to_run(row: &sqlx::postgres::PgRow) -> Run {
    Run {
        id: row.get("id"),
        account_id: row.get("account_id"),
        slug: row.get("slug"),
        pitch: row.get("pitch"),
        state: row.get("state"),
        error: row.get("error"),
        created_at: row.get("created_at"),
    }
}

fn to_stage(row: &sqlx::postgres::PgRow) -> RunStage {
    RunStage {
        stage_id: row.get("stage_id"),
        verdict: row.get("verdict"),
        score: row.get("score"),
        ts: row.get("ts"),
    }
}

pub async fn insert_run(pool: &PgPool, run: Run) -> Result<(), String> {
    sqlx::query(INSERT_RUN)
        .bind(run.id)
        .bind(run.account_id)
        .bind(run.slug)
        .bind(run.pitch)
        .bind(run.state)
        .bind(run.error)
        .bind(run.created_at)
        .execute(pool)
        .await
        .map(|_| ())
        .map_err(|e| e.to_string())
}

pub async fn update_run_state(
    pool: &PgPool,
    run_id: &str,
    state: &str,
    error: Option<&str>,
) -> Result<(), String> {
    sqlx::query(UPDATE_STATE)
        .bind(run_id)
        .bind(state)
        .bind(error)
        .execute(pool)
        .await
        .map(|_| ())
        .map_err(|e| e.to_string())
}

pub async fn append_stage(pool: &PgPool, run_id: &str, stage: RunStage) -> Result<(), String> {
    sqlx::query(INSERT_STAGE)
        .bind(run_id)
        .bind(stage.stage_id)
        .bind(stage.verdict)
        .bind(stage.score)
        .bind(now_unix())
        .execute(pool)
        .await
        .map(|_| ())
        .map_err(|e| e.to_string())
}

pub async fn list_runs(pool: &PgPool, account_id: &str) -> Result<Vec<Run>, String> {
    let rows = sqlx::query(LIST_RUNS)
        .bind(account_id)
        .fetch_all(pool)
        .await
        .map_err(|e| e.to_string())?;
    Ok(rows.iter().map(to_run).collect())
}

pub async fn get_run(pool: &PgPool, run_id: &str) -> Result<Option<Run>, String> {
    let row = sqlx::query(SELECT_RUN)
        .bind(run_id)
        .fetch_optional(pool)
        .await
        .map_err(|e| e.to_string())?;
    Ok(row.as_ref().map(to_run))
}

const DEL_STAGES: &str =
    "DELETE FROM run_stages WHERE run_id IN (SELECT id FROM runs WHERE account_id = $1)";

/// Delete an account's rows across all four tables in one transaction; returns #runs removed.
pub async fn delete_account(pool: &PgPool, account_id: &str) -> Result<u64, String> {
    let mut tx = pool.begin().await.map_err(|e| e.to_string())?;
    let q = |sql: &'static str| sqlx::query(sql).bind(account_id);
    q(DEL_STAGES)
        .execute(&mut *tx)
        .await
        .map_err(|e| e.to_string())?;
    let runs = q("DELETE FROM runs WHERE account_id = $1")
        .execute(&mut *tx)
        .await
        .map_err(|e| e.to_string())?
        .rows_affected();
    q("DELETE FROM sessions WHERE account_id = $1")
        .execute(&mut *tx)
        .await
        .map_err(|e| e.to_string())?;
    q("DELETE FROM users WHERE account_id = $1")
        .execute(&mut *tx)
        .await
        .map_err(|e| e.to_string())?;
    tx.commit().await.map_err(|e| e.to_string())?;
    Ok(runs)
}

pub async fn run_stages(pool: &PgPool, run_id: &str) -> Result<Vec<RunStage>, String> {
    let rows = sqlx::query(SELECT_STAGES)
        .bind(run_id)
        .fetch_all(pool)
        .await
        .map_err(|e| e.to_string())?;
    Ok(rows.iter().map(to_stage).collect())
}
