//! `GET /app` — the signed-in dashboard: a submit form (a one-line pitch, or a site URL + angle, plus a
//! validation-mode select) and the account's run history. Submission posts JSON to `POST /api/runs` via
//! a small inline script and navigates to the new run page. Unauthenticated visitors are sent to `/`.

use axum::extract::State;
use axum::http::HeaderMap;
use axum::response::{IntoResponse, Redirect, Response};
use maud::{html, Markup, PreEscaped};

use crate::datefmt::ymd_iso;
use crate::db::Run;
use crate::extract::account_from_headers;
use crate::state::AppState;

use super::layout::page;

const SUBMIT_JS: &str = "const f=document.getElementById('runform');\
f.addEventListener('submit',async(e)=>{e.preventDefault();const fd=new FormData(f);\
const pitch=(fd.get('pitch')||'').trim(),url=(fd.get('url')||'').trim();\
const body=pitch?{pitch}:{url,angle:fd.get('angle')||''};\
const btn=f.querySelector('button');btn.disabled=true;\
const r=await fetch('/api/runs',{method:'POST',headers:{'content-type':'application/json'},\
body:JSON.stringify(body)});if(r.status===201){location.href='/app/runs/'+(await r.json()).run_id;}\
else{btn.disabled=false;document.getElementById('formerr').textContent='Could not start — add a pitch or a URL.';}});";

fn submit_form() -> Markup {
    html! {
        form id="runform" {
            label for="pitch" { "One-sentence pitch" }
            textarea id="pitch" name="pitch" placeholder="An AI tutor that coaches nurses…" {}
            label for="url" { "…or a website URL to validate" }
            input id="url" name="url" placeholder="https://example.com";
            label for="angle" { "Optional angle for that company" }
            input id="angle" name="angle" placeholder="a new SMB product line";
            label for="mode" { "Validation mode" }
            select id="mode" name="mode" {
                option value="all" { "Full pipeline (all stages)" }
                option value="frame" { "Quick frame only" }
            }
            button type="submit" { "Validate idea" }
            p id="formerr" class="kill" {}
        }
    }
}

fn state_class(state: &str) -> &'static str {
    match state {
        "done" => "go",
        "error" | "cancelled" => "kill",
        _ => "muted",
    }
}

fn run_row(r: &Run) -> Markup {
    html! {
        a.row href=(format!("/app/runs/{}", r.id)) {
            span { (r.slug) }
            span.muted { (ymd_iso(r.created_at)) }
            span class={ "badge " (state_class(&r.state)) } { (r.state) }
        }
    }
}

fn history(runs: &[Run]) -> Markup {
    html! {
        div.card {
            h1 { "Your runs" }
            @if runs.is_empty() {
                p.muted { "No runs yet — validate your first idea above." }
            } @else {
                @for r in runs { (run_row(r)) }
            }
        }
    }
}

fn body(runs: &[Run]) -> Markup {
    html! {
        header.top {
            h1 { "Validate an idea" }
            form method="post" action="/auth/logout" { button { "Sign out" } }
        }
        div.card { (submit_form()) }
        (history(runs))
        script { (PreEscaped(SUBMIT_JS)) }
    }
}

/// Render the dashboard for the signed-in account, or redirect anonymous visitors to the landing page.
pub async fn app_page(State(st): State<AppState>, headers: HeaderMap) -> Response {
    let account = match account_from_headers(&headers, &st).await {
        Some(a) => a,
        None => return Redirect::to("/").into_response(),
    };
    let runs = st.db.list_runs(&account).await.unwrap_or_default();
    page("Dashboard", body(&runs)).into_response()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(id: &str, slug: &str, state: &str) -> Run {
        Run {
            id: id.into(),
            account_id: "acc".into(),
            slug: slug.into(),
            pitch: "p".into(),
            state: state.into(),
            error: None,
            created_at: 0,
        }
    }

    #[test]
    fn form_has_pitch_url_and_mode_fields() {
        let html = submit_form().into_string();
        assert!(html.contains("name=\"pitch\""));
        assert!(html.contains("name=\"url\""));
        assert!(html.contains("name=\"mode\""));
    }

    #[test]
    fn history_lists_runs_with_slug_and_link() {
        let runs = vec![run("abc", "ai-tutor", "done")];
        let html = history(&runs).into_string();
        assert!(html.contains("/app/runs/abc"));
        assert!(html.contains("ai-tutor"));
    }

    #[test]
    fn empty_history_shows_a_hint() {
        assert!(history(&[]).into_string().contains("No runs yet"));
    }
}
