//! The url-form of a run shells out to `pipeline.cli ingest` to turn a website (+ optional angle) into a
//! brief under the store. The run is orchestrated by [`crate::jobs_url`], which calls these helpers from a
//! background task so a slow ingest never blocks the request (which used to exceed Render's proxy timeout
//! and 502). This module owns only the paths, the argv inputs and the subprocess — and it captures the
//! subprocess's stderr so an ingest failure is reported on the run, never swallowed.

use std::path::{Path, PathBuf};
use std::process::Stdio;

use tokio::process::Command;

use crate::api_input::IngestArgs;
use crate::state::AppState;

/// A url submission: the site to read and an optional angle/new idea for that company.
pub struct UrlForm<'a> {
    pub url: &'a str,
    pub angle: &'a str,
}

/// Where ingested briefs for an account are written under the run store.
pub fn ideas_dir(st: &AppState, account: &str) -> PathBuf {
    Path::new(&st.config.store_dir)
        .join(account)
        .join("ingested")
}

/// The brief path a given slug ingests to.
pub fn brief_path(st: &AppState, account: &str, slug: &str) -> PathBuf {
    ideas_dir(st, account).join(format!("{slug}.md"))
}

/// Build the `pipeline.cli ingest` args for a submission.
pub fn ingest_args(form: &UrlForm, slug: &str, dir: &Path) -> IngestArgs {
    IngestArgs {
        url: form.url.to_string(),
        angle: form.angle.to_string(),
        slug: slug.to_string(),
        ideas_dir: dir.to_string_lossy().into_owned(),
    }
}

fn stderr_tail(bytes: &[u8]) -> String {
    let err = String::from_utf8_lossy(bytes);
    let s = err.trim();
    s.get(s.len().saturating_sub(600)..)
        .unwrap_or(s)
        .to_string()
}

/// Run `<python> -m pipeline.cli ingest ...`; on failure, return the stderr tail (never swallowed).
pub async fn run_ingest(python: &str, rest: &[String], token: &str) -> Result<(), String> {
    let out = Command::new(python)
        .args(rest)
        .env("PALGU_API_KEY", token)
        .stdin(Stdio::null())
        .output()
        .await
        .map_err(|e| e.to_string())?;
    if out.status.success() {
        return Ok(());
    }
    Err(format!(
        "ingest failed ({}): {}",
        out.status,
        stderr_tail(&out.stderr)
    ))
}

#[cfg(test)]
mod tests {
    use super::run_ingest;

    #[tokio::test]
    async fn run_ingest_reports_stderr_on_failure() {
        let rest = vec!["-c".to_string(), "echo boom 1>&2; exit 3".to_string()];
        let err = run_ingest("/bin/sh", &rest, "tok").await.unwrap_err();
        assert!(err.contains("boom"), "{err}");
        assert!(err.contains("ingest failed"));
    }

    #[tokio::test]
    async fn run_ingest_ok_on_success() {
        let rest = vec!["-c".to_string(), "true".to_string()];
        assert!(run_ingest("/bin/sh", &rest, "tok").await.is_ok());
    }
}
