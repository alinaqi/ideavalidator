//! Spawning the Python worker and streaming its stdout. [`WorkerSpawner`] is the injectable boundary:
//! the real [`ProcessSpawner`] runs `<python> -m worker.run_job ...` from the repo root with the Palgu
//! token in the environment (never logged), while tests use the in-memory fakes below. The returned
//! [`SpawnedWorker`] yields one stdout line at a time; the caller holds a [`CancelToken`] to stop it.

use std::path::{Path, PathBuf};
use std::process::Stdio;

use async_trait::async_trait;
use tokio::io::{AsyncBufReadExt, BufReader, Lines};
use tokio::process::{Child, ChildStdout, Command};
use tokio::sync::mpsc::{self, Receiver, Sender};

use crate::runs::CancelToken;

/// What to run: the brief to validate, where stage output goes, the caller's Palgu key, stage selection.
pub struct SpawnRequest {
    pub brief_path: PathBuf,
    pub out_dir: PathBuf,
    pub palgu_token: String,
    pub stages: String,
}

/// A live worker: its stdout arrives one line at a time until the process ends or is cancelled.
pub struct SpawnedWorker {
    pub lines: Receiver<String>,
}

#[async_trait]
pub trait WorkerSpawner: Send + Sync {
    async fn spawn(&self, req: SpawnRequest, cancel: CancelToken) -> Result<SpawnedWorker, String>;
}

/// Real spawner over `tokio::process`. `workdir` is the repo root; `python` is the interpreter path.
pub struct ProcessSpawner {
    python: String,
    workdir: PathBuf,
}

impl ProcessSpawner {
    pub fn new(python: String, workdir: PathBuf) -> Self {
        ProcessSpawner { python, workdir }
    }
}

fn build_command(python: &str, workdir: &Path, req: &SpawnRequest) -> Command {
    let mut cmd = Command::new(python);
    cmd.arg("-m")
        .arg("worker.run_job")
        .arg("--brief")
        .arg(&req.brief_path)
        .arg("--out")
        .arg(&req.out_dir)
        .arg("--stages")
        .arg(&req.stages)
        .current_dir(workdir)
        .env("PALGU_API_KEY", &req.palgu_token)
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    cmd
}

#[async_trait]
impl WorkerSpawner for ProcessSpawner {
    async fn spawn(&self, req: SpawnRequest, cancel: CancelToken) -> Result<SpawnedWorker, String> {
        let mut child = build_command(&self.python, &self.workdir, &req)
            .spawn()
            .map_err(|e| e.to_string())?;
        let stdout = child.stdout.take().ok_or("worker produced no stdout")?;
        let (tx, lines) = mpsc::channel(64);
        tokio::spawn(Pump { child, tx, cancel }.run(stdout));
        Ok(SpawnedWorker { lines })
    }
}

/// Owns the child while forwarding its stdout lines; kills it on cancel.
struct Pump {
    child: Child,
    tx: Sender<String>,
    cancel: CancelToken,
}

impl Pump {
    async fn run(mut self, stdout: ChildStdout) {
        let mut reader = BufReader::new(stdout).lines();
        while self.step(&mut reader).await {}
    }

    async fn step(&mut self, reader: &mut Lines<BufReader<ChildStdout>>) -> bool {
        tokio::select! {
            next = reader.next_line() => self.forward(next).await,
            _ = self.cancel.cancelled() => {
                let _ = self.child.kill().await;
                false
            }
        }
    }

    async fn forward(&self, next: std::io::Result<Option<String>>) -> bool {
        match next {
            Ok(Some(line)) => self.tx.send(line).await.is_ok(),
            _ => false,
        }
    }
}

/// A spawner that starts nothing and yields no lines; the default for surfaces that never run a job.
pub struct NoopSpawner;

#[async_trait]
impl WorkerSpawner for NoopSpawner {
    async fn spawn(
        &self,
        _req: SpawnRequest,
        _cancel: CancelToken,
    ) -> Result<SpawnedWorker, String> {
        let (_tx, lines) = mpsc::channel(1);
        Ok(SpawnedWorker { lines })
    }
}

#[cfg(test)]
pub struct FakeSpawner {
    pub lines: Vec<String>,
    pub wait_cancel: bool,
}

#[cfg(test)]
impl FakeSpawner {
    /// Spawn with a throwaway request — for tests that drive the worker loop directly.
    pub async fn spawn_for_test(&self, cancel: CancelToken) -> SpawnedWorker {
        let req = SpawnRequest {
            brief_path: "b.md".into(),
            out_dir: "/out".into(),
            palgu_token: "t".into(),
            stages: "all".into(),
        };
        self.spawn(req, cancel).await.unwrap()
    }
}

#[cfg(test)]
#[async_trait]
impl WorkerSpawner for FakeSpawner {
    async fn spawn(
        &self,
        _req: SpawnRequest,
        cancel: CancelToken,
    ) -> Result<SpawnedWorker, String> {
        let (tx, lines) = mpsc::channel(64);
        let scripted = self.lines.clone();
        let wait = self.wait_cancel;
        tokio::spawn(async move {
            for line in scripted {
                if tx.send(line).await.is_err() {
                    return;
                }
            }
            if wait {
                cancel.cancelled().await; // emulate a worker killed mid-run
            }
        });
        Ok(SpawnedWorker { lines })
    }
}

#[cfg(test)]
#[path = "worker_proc_tests.rs"]
mod tests;
