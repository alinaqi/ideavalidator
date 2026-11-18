//! Cancellation plumbing for in-flight runs. A [`CancelToken`] carries both a sticky flag (so a late
//! reader still sees the cancel) and a `Notify` (so a waiting worker wakes promptly to kill its child).
//! [`RunRegistry`] maps `run_id -> CancelToken` so a request handler can cancel a run the orchestrator
//! started on a background task.

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use tokio::sync::Notify;

/// Whether a run state is final (no worker is or will be running for it).
pub fn is_terminal(state: &str) -> bool {
    matches!(state, "done" | "error" | "cancelled")
}

/// A cheap, cloneable cancel signal shared between a request handler and a running worker.
#[derive(Clone, Default)]
pub struct CancelToken {
    flag: Arc<AtomicBool>,
    notify: Arc<Notify>,
}

impl CancelToken {
    pub fn new() -> Self {
        Self::default()
    }

    /// Mark cancelled and wake anyone waiting in [`cancelled`](Self::cancelled).
    pub fn cancel(&self) {
        self.flag.store(true, Ordering::SeqCst);
        self.notify.notify_waiters();
    }

    pub fn is_cancelled(&self) -> bool {
        self.flag.load(Ordering::SeqCst)
    }

    /// Resolve once cancelled (immediately if already cancelled).
    pub async fn cancelled(&self) {
        if self.is_cancelled() {
            return;
        }
        self.notify.notified().await;
    }
}

/// Thread-safe registry of the cancel tokens for currently-tracked runs.
#[derive(Clone, Default)]
pub struct RunRegistry {
    inner: Arc<Mutex<HashMap<String, CancelToken>>>,
}

impl RunRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn register(&self, run_id: &str, token: CancelToken) {
        self.inner.lock().unwrap().insert(run_id.to_string(), token);
    }

    pub fn remove(&self, run_id: &str) {
        self.inner.lock().unwrap().remove(run_id);
    }

    pub fn is_cancelled(&self, run_id: &str) -> bool {
        self.token(run_id).is_some_and(|t| t.is_cancelled())
    }

    /// Request cancellation; returns whether a run by that id was being tracked.
    pub fn cancel(&self, run_id: &str) -> bool {
        match self.token(run_id) {
            Some(t) => {
                t.cancel();
                true
            }
            None => false,
        }
    }

    fn token(&self, run_id: &str) -> Option<CancelToken> {
        self.inner.lock().unwrap().get(run_id).cloned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn token_reports_and_resolves_cancel() {
        let t = CancelToken::new();
        assert!(!t.is_cancelled());
        t.cancel();
        assert!(t.is_cancelled());
        t.cancelled().await; // already cancelled -> returns at once
    }

    #[test]
    fn registry_cancels_known_runs_only() {
        let reg = RunRegistry::new();
        let token = CancelToken::new();
        reg.register("r1", token.clone());
        assert!(reg.cancel("r1"));
        assert!(token.is_cancelled());
        assert!(reg.is_cancelled("r1"));
        assert!(!reg.cancel("missing"));
    }

    #[test]
    fn terminal_states_are_recognised() {
        for s in ["done", "error", "cancelled"] {
            assert!(is_terminal(s), "{s} should be terminal");
        }
        for s in ["pending", "running", ""] {
            assert!(!is_terminal(s), "{s} should be live");
        }
    }

    #[test]
    fn remove_drops_the_token() {
        let reg = RunRegistry::new();
        reg.register("r1", CancelToken::new());
        reg.remove("r1");
        assert!(!reg.is_cancelled("r1"));
        assert!(!reg.cancel("r1"));
    }
}
