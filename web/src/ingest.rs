//! The url-form of a run: shell out to `pipeline.cli ingest` to turn a website (plus an optional angle)
//! into a full idea brief under the store, then hand that brief to [`JobManager::start_with_brief`]. The
//! argv is built by the unit-tested [`crate::api_input::ingest_argv`]; the process spawn here needs the
//! engine + network, so it is covered by an integration test, not the required unit gate.

use std::path::{Path, PathBuf};
use std::process::Stdio;

use tokio::process::Command;

use crate::api_input::{ingest_argv, IngestArgs};
use crate::brief::slug;
use crate::jobs::{BriefRef, JobManager};
use crate::state::AppState;

/// A url submission: the site to read and an optional angle/new idea for that company.
pub struct UrlForm<'a> {
    pub url: &'a str,
    pub angle: &'a str,
}

fn ideas_dir(st: &AppState, account: &str) -> PathBuf {
    Path::new(&st.config.store_dir)
        .join(account)
        .join("ingested")
}

async fn palgu_key(st: &AppState, account: &str) -> Result<String, String> {
    let user = st.db.get_user(account).await?.ok_or("not signed in")?;
    st.cipher.decrypt(&user.enc_token)
}

async fn run_ingest(python: &str, rest: &[String], token: &str) -> Result<(), String> {
    let status = Command::new(python)
        .args(rest)
        .env("PALGU_API_KEY", token)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .await
        .map_err(|e| e.to_string())?;
    status
        .success()
        .then_some(())
        .ok_or_else(|| "ingest failed".to_string())
}

fn ingest_args(form: &UrlForm, run_slug: &str, dir: &Path) -> IngestArgs {
    IngestArgs {
        url: form.url.to_string(),
        angle: form.angle.to_string(),
        slug: run_slug.to_string(),
        ideas_dir: dir.to_string_lossy().into_owned(),
    }
}

/// Ingest `form.url` into a brief, then start a validation run from it; returns the new `run_id`.
pub async fn ingest_and_start(
    st: &AppState,
    account: &str,
    form: UrlForm<'_>,
) -> Result<String, String> {
    let token = palgu_key(st, account).await?;
    let dir = ideas_dir(st, account);
    let key = if form.angle.is_empty() {
        form.url
    } else {
        form.angle
    };
    let run_slug = slug(key);
    let argv = ingest_argv(&st.config.python_bin, &ingest_args(&form, &run_slug, &dir));
    run_ingest(&argv[0], &argv[1..], &token).await?;
    let brief = BriefRef {
        slug: run_slug.clone(),
        pitch: format!("Ingested from {}", form.url),
        brief_path: dir.join(format!("{run_slug}.md")),
    };
    JobManager::new(st.clone())
        .start_with_brief(account, brief)
        .await
}
