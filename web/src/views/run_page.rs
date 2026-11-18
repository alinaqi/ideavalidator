//! `GET /app/runs/:id` — the live run page. It renders the ten-stage checklist, subscribes to
//! `GET /api/runs/:id/stream` (SSE) with a small inline script to mark stages done as they land, and on
//! completion loads the GO / PIVOT / KILL memo from `GET /api/runs/:id/report`. Revisiting a finished
//! run shows the stored stages immediately. Runs the caller does not own redirect to the dashboard.

use axum::extract::{Path, State};
use axum::http::HeaderMap;
use axum::response::{IntoResponse, Redirect, Response};
use maud::{html, Markup, PreEscaped};

use crate::db::{Run, RunStage};
use crate::extract::account_from_headers;
use crate::state::AppState;

use super::layout::page;
use super::run_script::run_js;

const STAGES: [(&str, &str); 10] = [
    ("frame", "Frame the opportunity"),
    ("classify", "Classify category & model"),
    ("problem", "Validate the problem"),
    ("market", "Understand the market"),
    ("icp", "ICP & beachhead vertical"),
    ("swot", "SWOT / TOWS"),
    ("wtp", "Willingness to pay"),
    ("economics", "Day-one economics"),
    ("risks", "Assumption & risk map"),
    ("decision", "Decision memo"),
];

fn stage_item(id: &str, label: &str, done: bool) -> Markup {
    html! {
        li id=(format!("stage-{id}")) class=(if done { "done" } else { "" }) {
            span.lbl { (label) }
            span.v.muted { (if done { "done" } else { "" }) }
        }
    }
}

/// The host for an ingested run (`Ingested from https://www.x.org` → `x.org`), else the raw url.
fn host_of(url: &str) -> String {
    let no_scheme = url.split("://").last().unwrap_or(url);
    let host = no_scheme.split('/').next().unwrap_or(no_scheme);
    host.strip_prefix("www.").unwrap_or(host).to_string()
}

/// A human title for the run: the site host for an ingested run, else the slug.
fn display_title(run: &Run) -> String {
    match run.pitch.strip_prefix("Ingested from ") {
        Some(url) => host_of(url),
        None => run.slug.clone(),
    }
}

/// The banner shown while a run is still `pending` (before the first stage completes).
fn pending_msg(run: &Run) -> &'static str {
    if run.pitch.starts_with("Ingested from ") {
        "Reading the website and preparing the brief…"
    } else {
        "Preparing the brief…"
    }
}

/// The state pill, progress bar, counts, elapsed clock and error line above the stage list.
fn progress_head(run: &Run) -> Markup {
    html! {
        div.statrow {
            span.muted { "State: " span id="state" { (run.state) } }
            span.muted { span id="pcount" { "0 / 10" } " · " span id="elapsed" { "0:00" } }
        }
        div.pbar id="pbar" { i {} }
        p.phase id="phase" {}
        p id="runerr" class="kill" { (run.error.clone().unwrap_or_default()) }
    }
}

fn stage_list(stages: &[RunStage]) -> Markup {
    html! {
        ol.stages {
            @for (id, label) in STAGES {
                (stage_item(id, label, stages.iter().any(|s| s.stage_id == id)))
            }
        }
    }
}

fn body(run: &Run, stages: &[RunStage]) -> Markup {
    html! {
        header.top {
            h1 { (display_title(run)) }
            div.topright {
                @if !crate::runs::is_terminal(&run.state) {
                    button id="stopbtn" class="stop" { "Stop run" }
                }
                a href="/app" { "← Dashboard" }
            }
        }
        div.card {
            (progress_head(run))
            (stage_list(stages))
        }
        iframe id="memo" style="display:none;width:100%;height:60vh;border:1px solid var(--line);border-radius:12px" {}
        script { (PreEscaped(run_js(&run.id, &run.state, pending_msg(run)))) }
    }
}

async fn load_owned(st: &AppState, account: &str, id: &str) -> Option<Run> {
    st.db
        .get_run(id)
        .await
        .ok()
        .flatten()
        .filter(|r| r.account_id == account)
}

/// Render the live run page, redirecting anonymous or non-owning callers away.
pub async fn run_page(
    State(st): State<AppState>,
    headers: HeaderMap,
    Path(id): Path<String>,
) -> Response {
    let account = match account_from_headers(&headers, &st).await {
        Some(a) => a,
        None => return Redirect::to("/").into_response(),
    };
    let run = match load_owned(&st, &account, &id).await {
        Some(r) => r,
        None => return Redirect::to("/app").into_response(),
    };
    let stages = st.db.run_stages(&id).await.unwrap_or_default();
    page("Run", body(&run, &stages)).into_response()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run() -> Run {
        Run {
            id: "r1".into(),
            account_id: "acc".into(),
            slug: "ai-tutor".into(),
            pitch: "p".into(),
            state: "running".into(),
            error: None,
            created_at: 0,
        }
    }

    #[test]
    fn renders_all_stage_anchors() {
        let html = body(&run(), &[]).into_string();
        for (id, _) in STAGES {
            assert!(html.contains(&format!("stage-{id}")), "missing {id}");
        }
        assert!(html.contains("Willingness to pay"));
    }

    #[test]
    fn stored_stages_are_marked_done() {
        let stages = vec![RunStage {
            stage_id: "frame".into(),
            verdict: Some("GO".into()),
            score: Some(4.0),
            ts: 0,
        }];
        let html = stage_list(&stages).into_string();
        assert!(html.contains("id=\"stage-frame\" class=\"done\""));
    }

    #[test]
    fn title_is_the_host_for_an_ingested_run() {
        let mut r = run();
        r.pitch = "Ingested from https://www.harness-hub.org".into();
        assert_eq!(display_title(&r), "harness-hub.org");
        assert!(pending_msg(&r).contains("Reading the website"));
    }

    #[test]
    fn title_is_the_slug_for_a_pitch_run() {
        assert_eq!(display_title(&run()), "ai-tutor");
    }

    #[test]
    fn stop_button_shows_only_while_live() {
        assert!(body(&run(), &[]).into_string().contains("id=\"stopbtn\""));
        let mut r = run();
        r.state = "done".into();
        assert!(!body(&r, &[]).into_string().contains("id=\"stopbtn\""));
    }

    #[test]
    fn progress_head_has_bar_and_clock() {
        let html = progress_head(&run()).into_string();
        assert!(html.contains("id=\"pbar\""));
        assert!(html.contains("id=\"elapsed\""));
        assert!(html.contains("id=\"phase\""));
    }
}
