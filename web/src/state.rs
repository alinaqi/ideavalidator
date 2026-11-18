//! Shared application state handed to every handler via axum `State`. All heavy collaborators sit behind
//! `Arc`/trait objects so the whole thing is cheap to clone and trivial to fake in tests.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use tokio::sync::Semaphore;

use crate::config::Config;
use crate::crypto::Cipher;
use crate::db::Db;
use crate::mcp::sessions::McpSessions;
use crate::palgu::{DeviceStart, PalguHttp};
use crate::runs::RunRegistry;
use crate::sse::SseHub;
use crate::worker_proc::WorkerSpawner;

/// An in-flight device sign-in, keyed by the opaque `poll_token` returned to the client.
#[derive(Clone)]
pub struct Pending {
    pub device_code: String,
    pub interval: u64,
}

impl From<&DeviceStart> for Pending {
    fn from(d: &DeviceStart) -> Self {
        Pending {
            device_code: d.device_code.clone(),
            interval: d.interval,
        }
    }
}

/// Map of `poll_token -> Pending` for device flows awaiting approval.
pub type PendingMap = Arc<Mutex<HashMap<String, Pending>>>;

#[derive(Clone)]
pub struct AppState {
    pub db: Arc<dyn Db>,
    pub palgu: Arc<dyn PalguHttp>,
    pub cipher: Arc<Cipher>,
    pub config: Config,
    pub pending: PendingMap,
    /// Spawns the Python worker per run (real process in prod, a fake in tests).
    pub spawner: Arc<dyn WorkerSpawner>,
    /// Live per-run progress fan-out for SSE.
    pub hub: Arc<SseHub>,
    /// Bounds the number of concurrently-running workers.
    pub sem: Arc<Semaphore>,
    /// Cancel tokens for in-flight runs.
    pub runs: RunRegistry,
    /// Live MCP session -> account bindings (the hosted `/mcp` sign-in map).
    pub mcp: McpSessions,
}

/// A fresh, empty pending-flow map (fields are public, so callers build `AppState` as a literal).
pub fn new_pending_map() -> PendingMap {
    Arc::new(Mutex::new(HashMap::new()))
}
