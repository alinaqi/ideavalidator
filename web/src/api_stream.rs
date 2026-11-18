//! `GET /api/runs/:id/stream` — a Server-Sent Events feed of a run's live progress, bridged from the P2
//! broadcast hub. Each [`Event`] becomes a named SSE frame carrying a small JSON payload, so the run
//! page can update per-stage without polling. Ownership is enforced first (a stranger's run reads 404).

use std::convert::Infallible;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::sse::{Event as SseEvent, Sse};
use axum::response::{IntoResponse, Response};
use serde_json::{json, Value};
use tokio_stream::wrappers::BroadcastStream;
use tokio_stream::StreamExt;

use crate::api::owned_run;
use crate::events::Event;
use crate::extract::CurrentAccount;
use crate::state::AppState;

fn event_json(ev: &Event) -> (&'static str, Value) {
    match ev {
        Event::Stage {
            stage,
            verdict,
            score,
        } => (
            "stage",
            json!({ "stage": stage, "verdict": verdict, "score": score }),
        ),
        Event::Done => ("done", json!({})),
        Event::Cancelled => ("cancelled", json!({})),
        Event::Error { error } => ("error", json!({ "error": error })),
        Event::Unknown => ("unknown", json!({})),
    }
}

fn to_frame(ev: &Event) -> SseEvent {
    let (name, data) = event_json(ev);
    SseEvent::default().event(name).data(data.to_string())
}

/// Stream a run's events as SSE. The response stays open; the client closes it on navigation.
pub async fn run_stream(
    CurrentAccount(account): CurrentAccount,
    State(st): State<AppState>,
    Path(id): Path<String>,
) -> Response {
    if owned_run(&st, &account, &id).await.is_err() {
        return StatusCode::NOT_FOUND.into_response();
    }
    let rx = st.hub.subscribe(&id);
    let stream = BroadcastStream::new(rx)
        .filter_map(|r| r.ok().map(|ev| Ok::<_, Infallible>(to_frame(&ev))));
    Sse::new(stream).into_response()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stage_event_maps_to_a_named_json_frame() {
        let ev = Event::Stage {
            stage: "market".into(),
            verdict: Some("GO".into()),
            score: Some(4.2),
        };
        let (name, data) = event_json(&ev);
        assert_eq!(name, "stage");
        assert_eq!(data["stage"], "market");
        assert_eq!(data["verdict"], "GO");
    }

    #[test]
    fn terminal_events_have_their_own_names() {
        assert_eq!(event_json(&Event::Done).0, "done");
        assert_eq!(event_json(&Event::Cancelled).0, "cancelled");
        assert_eq!(event_json(&Event::Error { error: "x".into() }).0, "error");
    }
}
