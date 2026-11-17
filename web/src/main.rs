//! Entrypoint: build shared state (Postgres, cipher, real Palgu HTTP) and serve the router.
//! Transport + real-IO wiring only, so it stays out of unit tests.

use std::path::PathBuf;
use std::sync::Arc;

use tokio::sync::Semaphore;

use ideavalidator_web::config::Config;
use ideavalidator_web::crypto::Cipher;
use ideavalidator_web::db::Db;
use ideavalidator_web::db_pg::PgDb;
use ideavalidator_web::mcp::sessions::new_mcp_sessions;
use ideavalidator_web::palgu::PalguHttp;
use ideavalidator_web::palgu_http::ReqwestHttp;
use ideavalidator_web::router::app;
use ideavalidator_web::runs::RunRegistry;
use ideavalidator_web::sse::SseHub;
use ideavalidator_web::state::{new_pending_map, AppState};
use ideavalidator_web::worker_proc::{ProcessSpawner, WorkerSpawner};

type BoxError = Box<dyn std::error::Error>;

fn build_spawner(cfg: &Config) -> Arc<dyn WorkerSpawner> {
    let workdir = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    Arc::new(ProcessSpawner::new(cfg.python_bin.clone(), workdir))
}

async fn build_state(cfg: Config) -> Result<AppState, BoxError> {
    let cipher = Arc::new(Cipher::from_env_key(&cfg.token_enc_key)?);
    let pg = PgDb::connect(&cfg.database_url).await?;
    pg.migrate().await?;
    let db: Arc<dyn Db> = Arc::new(pg);
    let palgu: Arc<dyn PalguHttp> = Arc::new(ReqwestHttp::new(cfg.palgu_origin.clone()));
    let sem = Arc::new(Semaphore::new(cfg.max_concurrent_runs));
    let spawner = build_spawner(&cfg);
    Ok(AppState {
        db,
        palgu,
        cipher,
        config: cfg,
        pending: new_pending_map(),
        spawner,
        hub: Arc::new(SseHub::new()),
        sem,
        runs: RunRegistry::new(),
        mcp: new_mcp_sessions(),
    })
}

#[tokio::main]
async fn main() -> Result<(), BoxError> {
    let cfg = Config::from_env();
    let addr = cfg.addr;
    let state = build_state(cfg).await?;
    let listener = tokio::net::TcpListener::bind(addr).await?;
    println!("ideavalidator-web listening on http://{addr}");
    axum::serve(listener, app(state)).await?;
    Ok(())
}
