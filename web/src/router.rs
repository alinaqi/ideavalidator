//! HTTP routing: liveness, the JSON auth endpoints, the server-rendered dashboard pages and the REST +
//! SSE run API. All handlers share one [`AppState`]; `/mcp` lands in a later phase on the same builder.

use axum::routing::{get, post};
use axum::Router;

use crate::mcp::http as mcp_http;
use crate::state::AppState;
use crate::{api, api_stream, auth, reqcheck, views};

fn api_routes() -> Router<AppState> {
    Router::new()
        .route("/api/runs", post(api::create_run).get(api::list_runs))
        .route("/api/runs/:id", get(api::run_status))
        .route("/api/runs/:id/cancel", post(api::cancel_run))
        .route("/api/runs/:id/report", get(api::run_report))
        .route("/api/runs/:id/stream", get(api_stream::run_stream))
        .route("/api/v1/requirements/check", post(reqcheck::check))
}

fn page_routes() -> Router<AppState> {
    Router::new()
        .route("/", get(views::landing::landing))
        .route("/app", get(views::app_page::app_page))
        .route("/app/runs/:id", get(views::run_page::run_page))
}

/// The application router, wired to shared [`AppState`].
pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/healthz", get(healthz))
        .route("/auth/start", post(auth::start))
        .route("/auth/poll", post(auth::poll))
        .route("/auth/logout", post(auth::logout))
        .route("/mcp", post(mcp_http::mcp_post).get(mcp_http::mcp_get))
        .merge(page_routes())
        .merge(api_routes())
        .with_state(state)
}

async fn healthz() -> &'static str {
    "ok"
}
