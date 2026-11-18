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
            span { (label) }
            span.v.muted { (if done { "done" } else { "…" }) }
        }
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

fn run_js(id: &str, state: &str) -> String {
    format!(
        "const id='{id}';const es=new EventSource('/api/runs/'+id+'/stream');\
es.addEventListener('stage',e=>{{const d=JSON.parse(e.data);const li=document.getElementById('stage-'+d.stage);\
if(li){{li.classList.add('done');li.querySelector('.v').textContent=d.verdict||'done';}}}});\
es.addEventListener('done',()=>{{es.close();set('done');}});es.addEventListener('cancelled',()=>{{es.close();set('cancelled');}});\
function set(s){{document.getElementById('state').textContent=s;if(s==='done')show();}}\
function show(){{const f=document.getElementById('memo');f.src='/api/runs/'+id+'/report';f.style.display='block';}}\
async function poll(){{try{{const d=await(await fetch('/api/runs/'+id)).json();document.getElementById('state').textContent=d.state;\
if(d.state==='error'){{document.getElementById('runerr').textContent=d.error||'failed';clearInterval(t);}}\
else if(d.state==='done'){{clearInterval(t);show();}}}}catch(e){{}}}}\
var t=setInterval(poll,4000);if('{state}'==='done')show();"
    )
}

fn body(run: &Run, stages: &[RunStage]) -> Markup {
    html! {
        header.top {
            h1 { (run.slug) }
            a href="/app" { "← Dashboard" }
        }
        div.card {
            p.muted { "State: " span id="state" { (run.state) } }
            p id="runerr" class="kill" { (run.error.clone().unwrap_or_default()) }
            (stage_list(stages))
        }
        iframe id="memo" style="display:none;width:100%;height:60vh;border:1px solid var(--line);border-radius:12px" {}
        script { (PreEscaped(run_js(&run.id, &run.state))) }
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
    fn script_wires_the_event_source() {
        let js = run_js("r1", "running");
        assert!(js.contains("EventSource('/api/runs/'+id+'/stream')"));
        assert!(js.contains("'/api/runs/'+id+'/report'"));
    }
}
