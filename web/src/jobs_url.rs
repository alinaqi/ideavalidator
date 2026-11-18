//! Async URL-ingest run. `POST /api/runs {url, angle}` returns a `run_id` immediately; a background task
//! then shells out to `pipeline.cli ingest` and, on success, runs the worker. This means a slow ingest no
//! longer blocks the HTTP request (which previously exceeded Render's proxy timeout → 502), and an ingest
//! failure is recorded on the run (`state = "error"` with the message), not returned as a 502.

use crate::api_input::ingest_argv;
use crate::db::{now_unix, Run};
use crate::ingest::{brief_path, ideas_dir, ingest_args, run_ingest, UrlForm};
use crate::jobs::{decrypt_token, new_run_id, run_dir};
use crate::jobs_run::{guarded_run, SpawnCtx};
use crate::runs::CancelToken;
use crate::state::AppState;

struct UrlRun {
    st: AppState,
    account: String,
    run_id: String,
    url: String,
    angle: String,
    slug: String,
    cancel: CancelToken,
}

/// A readable slug from a URL: drop the scheme and `www.`, keep host + path.
/// `https://www.harness-hub.org` → `harness-hub-org`.
fn url_slug(url: &str) -> String {
    let no_scheme = url.split("://").last().unwrap_or(url);
    let no_www = no_scheme.strip_prefix("www.").unwrap_or(no_scheme);
    crate::brief::slug(&no_www.replace(['.', '/'], " "))
}

/// A fresh `pending` run row for a URL submission (`key` = account, run_id, slug).
fn url_run_row(key: (&str, &str, &str), url: &str) -> Run {
    Run {
        id: key.1.to_string(),
        account_id: key.0.to_string(),
        slug: key.2.to_string(),
        pitch: format!("Ingested from {url}"),
        state: "pending".to_string(),
        error: None,
        created_at: now_unix(),
    }
}

/// Insert the run, return its id now, and ingest + run in the background.
pub async fn start_url(st: &AppState, account: &str, form: UrlForm<'_>) -> Result<String, String> {
    let run_id = new_run_id();
    let slug = if form.angle.is_empty() {
        url_slug(form.url)
    } else {
        crate::brief::slug(form.angle)
    };
    st.db
        .insert_run(url_run_row((account, &run_id, &slug), form.url))
        .await?;
    let cancel = CancelToken::new();
    st.runs.register(&run_id, cancel.clone());
    tokio::spawn(drive(UrlRun {
        st: st.clone(),
        account: account.to_string(),
        run_id: run_id.clone(),
        url: form.url.to_string(),
        angle: form.angle.to_string(),
        slug,
        cancel,
    }));
    Ok(run_id)
}

async fn do_ingest(j: &UrlRun, token: &str) -> Result<(), String> {
    let dir = ideas_dir(&j.st, &j.account);
    let form = UrlForm {
        url: &j.url,
        angle: &j.angle,
    };
    let argv = ingest_argv(&j.st.config.python_bin, &ingest_args(&form, &j.slug, &dir));
    run_ingest(&argv[0], &argv[1..], token).await
}

async fn fail(j: &UrlRun, msg: &str) {
    let _ =
        j.st.db
            .update_run_state(&j.run_id, "error", Some(msg))
            .await;
    j.st.runs.remove(&j.run_id);
}

fn ctx_for(j: &UrlRun, token: String) -> SpawnCtx {
    SpawnCtx {
        run_id: j.run_id.clone(),
        brief_path: brief_path(&j.st, &j.account, &j.slug),
        out_dir: run_dir(&j.st, &j.account, &j.run_id),
        token,
        cancel: j.cancel.clone(),
    }
}

async fn drive(j: UrlRun) {
    let token = match decrypt_token(&j.st, &j.account).await {
        Ok(t) => t,
        Err(e) => return fail(&j, &e).await,
    };
    if let Err(e) = do_ingest(&j, &token).await {
        return fail(&j, &e).await;
    }
    guarded_run(j.st.clone(), ctx_for(&j, token)).await;
}

#[cfg(test)]
mod tests {
    use super::{url_run_row, url_slug};

    #[test]
    fn url_slug_is_readable_host() {
        assert_eq!(url_slug("https://www.harness-hub.org"), "harness-hub-org");
        assert_eq!(url_slug("https://harness-hub.org"), "harness-hub-org");
        assert_eq!(
            url_slug("http://example.com/path/to"),
            "example-com-path-to"
        );
    }

    #[test]
    fn url_run_row_is_pending_with_ingest_pitch() {
        let r = url_run_row(
            ("acc", "r1", "harness-hub-central"),
            "https://harness-hub.org",
        );
        assert_eq!(r.state, "pending");
        assert_eq!(r.slug, "harness-hub-central");
        assert_eq!(r.account_id, "acc");
        assert!(r.pitch.contains("https://harness-hub.org"));
    }
}
