//! End-to-end tests for the run REST API and the dashboard pages, driven through the real axum router
//! with an in-memory DB, a scripted Palgu fake and the no-op worker spawner. No network, no Postgres,
//! no Python — the required gate runs these as-is.

use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use axum::body::Body;
use axum::http::{header, Request, StatusCode};
use axum::Router;
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

use ideavalidator_web::config::Config;
use ideavalidator_web::crypto::Cipher;
use ideavalidator_web::db::InMemoryDb;
use ideavalidator_web::palgu::PalguHttp;
use ideavalidator_web::router::app;
use ideavalidator_web::runs::RunRegistry;
use ideavalidator_web::sse::SseHub;
use ideavalidator_web::state::{new_pending_map, AppState};
use ideavalidator_web::worker_proc::NoopSpawner;
use tokio::sync::Semaphore;

const KEY_HEX: &str = "2222222222222222222222222222222222222222222222222222222222222222";

struct FakePalgu {
    token: Mutex<Vec<Value>>,
}

#[async_trait]
impl PalguHttp for FakePalgu {
    async fn post_json(&self, path: &str, _body: Value) -> Result<Value, String> {
        if path == "/auth/device/code" {
            Ok(
                json!({"ok": true, "body": {"device_code": "dc", "user_code": "WXYZ",
                "verification_uri": "https://palgu.ai/connect", "interval": 5, "expires_in": 600}}),
            )
        } else {
            Ok(self.token.lock().unwrap().remove(0))
        }
    }
    async fn get_json(&self, _path: &str, _bearer: &str) -> Result<Value, String> {
        Ok(Value::Null)
    }
}

fn token_success() -> Value {
    json!({"ok": true, "status": 200, "body": {"access_token": "k-1",
        "account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "pro"}}})
}

fn test_state() -> AppState {
    let store = std::env::temp_dir()
        .join(format!("iv-api-{}", std::process::id()))
        .to_string_lossy()
        .into_owned();
    let cfg = Config::from(move |k| match k {
        "TOKEN_ENC_KEY" => Some(KEY_HEX.to_string()),
        "IV_STORE" => Some(store.clone()),
        _ => None,
    });
    AppState {
        db: Arc::new(InMemoryDb::new()),
        palgu: Arc::new(FakePalgu {
            token: Mutex::new(vec![token_success()]),
        }),
        cipher: Arc::new(Cipher::from_env_key(KEY_HEX).unwrap()),
        config: cfg,
        pending: new_pending_map(),
        spawner: Arc::new(NoopSpawner),
        hub: Arc::new(SseHub::new()),
        sem: Arc::new(Semaphore::new(2)),
        runs: RunRegistry::new(),
        mcp: ideavalidator_web::mcp::sessions::new_mcp_sessions(),
    }
}

async fn send(router: Router, req: Request<Body>) -> (StatusCode, Value) {
    let resp = router.oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

fn post(uri: &str, cookie: Option<&str>, body: Value) -> Request<Body> {
    let mut b = Request::builder()
        .method("POST")
        .uri(uri)
        .header(header::CONTENT_TYPE, "application/json");
    if let Some(c) = cookie {
        b = b.header(header::COOKIE, c);
    }
    b.body(Body::from(body.to_string())).unwrap()
}

fn get(uri: &str, cookie: &str) -> Request<Body> {
    Request::builder()
        .uri(uri)
        .header(header::COOKIE, cookie)
        .body(Body::empty())
        .unwrap()
}

async fn sign_in(router: &Router) -> String {
    let (_s, start) = send(router.clone(), post("/auth/start", None, json!({}))).await;
    let token = start["poll_token"].as_str().unwrap().to_string();
    let resp = router
        .clone()
        .oneshot(post("/auth/poll", None, json!({ "poll_token": token })))
        .await
        .unwrap();
    let cookie = resp
        .headers()
        .get(header::SET_COOKIE)
        .unwrap()
        .to_str()
        .unwrap();
    cookie.split(';').next().unwrap().to_string()
}

#[tokio::test]
async fn create_run_requires_authentication() {
    let (status, _) = send(
        app(test_state()),
        post("/api/runs", None, json!({"pitch": "an idea"})),
    )
    .await;
    assert_eq!(status, StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn empty_submission_is_rejected() {
    let router = app(test_state());
    let cookie = sign_in(&router).await;
    let (status, body) = send(router, post("/api/runs", Some(&cookie), json!({}))).await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["error"].is_string());
}

#[tokio::test]
async fn pitch_run_is_created_listed_and_statusable() {
    let router = app(test_state());
    let cookie = sign_in(&router).await;
    let (status, created) = send(
        router.clone(),
        post(
            "/api/runs",
            Some(&cookie),
            json!({"pitch": "an AI tutor for nurses"}),
        ),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let run_id = created["run_id"].as_str().unwrap().to_string();

    let (_s, list) = send(router.clone(), get("/api/runs", &cookie)).await;
    assert_eq!(list["runs"][0]["run_id"], run_id);
    assert_eq!(list["runs"][0]["slug"], "an-ai-tutor-for-nurses");

    let (status, prog) = send(router, get(&format!("/api/runs/{run_id}"), &cookie)).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(prog["total"], 10);
    assert_eq!(prog["run_id"], run_id);
}

#[tokio::test]
async fn unknown_run_is_404() {
    let router = app(test_state());
    let cookie = sign_in(&router).await;
    let (status, _) = send(router, get("/api/runs/does-not-exist", &cookie)).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn landing_and_dashboard_render_html() {
    let router = app(test_state());
    let resp = router
        .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = resp.into_body().collect().await.unwrap().to_bytes();
    let html = String::from_utf8_lossy(&body);
    assert!(html.contains("Sign in with Palgu"));
    assert!(html.contains("<!DOCTYPE html>"));
}
