//! The requirements-check worker boundary (ADR 0014). [`ReqChecker`] is injectable: the real
//! [`ProcessChecker`] runs `<python> -m worker.req_check` from the repo root, writes the request to its
//! stdin, puts the caller's Palgu key in `PALGU_API_KEY` (never logged, never on the command line) and
//! reads the one `{"status","body"}` line it prints. The child is killed if the caller gives up.

use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Arc;

use async_trait::async_trait;
use serde_json::Value;
use tokio::io::AsyncWriteExt;
use tokio::process::Command;
use tokio::sync::Semaphore;

/// What the worker answered: the HTTP status to return and the body to relay unchanged.
#[derive(Debug, Clone, PartialEq)]
pub struct CheckReply {
    pub status: u16,
    pub body: Value,
}

#[async_trait]
pub trait ReqChecker: Send + Sync {
    async fn check(&self, body: Value, token: String) -> Result<CheckReply, String>;
}

/// Parse the worker's stdout: the last non-empty line must be `{"status": u16, "body": {...}}`.
pub fn parse_reply(stdout: &str) -> Result<CheckReply, String> {
    let line = stdout
        .lines()
        .rev()
        .find(|l| !l.trim().is_empty())
        .ok_or("worker printed nothing")?;
    let v: Value = serde_json::from_str(line).map_err(|_| "worker printed non-JSON")?;
    let status = v["status"].as_u64().ok_or("worker reply has no status")?;
    let status = u16::try_from(status).map_err(|_| "worker status out of range")?;
    Ok(CheckReply {
        status,
        body: v["body"].clone(),
    })
}

/// Real checker over `tokio::process`, bounded by its own semaphore (checks are short and separate
/// from the long validation runs).
pub struct ProcessChecker {
    python: String,
    workdir: PathBuf,
    slots: Arc<Semaphore>,
}

impl ProcessChecker {
    pub fn new(python: String, workdir: PathBuf, max_concurrent: usize) -> Self {
        ProcessChecker {
            python,
            workdir,
            slots: Arc::new(Semaphore::new(max_concurrent.max(1))),
        }
    }

    fn command(&self, token: &str) -> Command {
        let mut cmd = Command::new(&self.python);
        cmd.args(["-m", "worker.req_check"])
            .current_dir(&self.workdir)
            .env("PALGU_API_KEY", token)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit()) // counts-only log lines reach the service logs
            .kill_on_drop(true);
        cmd
    }
}

#[async_trait]
impl ReqChecker for ProcessChecker {
    async fn check(&self, body: Value, token: String) -> Result<CheckReply, String> {
        let _slot = self.slots.acquire().await.map_err(|e| e.to_string())?;
        let mut child = self.command(&token).spawn().map_err(|e| e.to_string())?;
        let mut stdin = child.stdin.take().ok_or("worker has no stdin")?;
        stdin
            .write_all(body.to_string().as_bytes())
            .await
            .map_err(|e| e.to_string())?;
        drop(stdin); // EOF: the worker reads the whole request
        let out = child.wait_with_output().await.map_err(|e| e.to_string())?;
        parse_reply(&String::from_utf8_lossy(&out.stdout))
    }
}

/// A checker that is never available; the default for tests that never call the route.
pub struct UnavailableChecker;

#[async_trait]
impl ReqChecker for UnavailableChecker {
    async fn check(&self, _body: Value, _token: String) -> Result<CheckReply, String> {
        Err("requirements check is not configured".into())
    }
}

#[cfg(test)]
#[path = "reqcheck_proc_tests.rs"]
mod tests;
