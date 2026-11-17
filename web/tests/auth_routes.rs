//! End-to-end tests for the auth routes and the `CurrentAccount` extractor, driven through the real
//! axum router with an in-memory DB and a scripted Palgu fake. No network, no Postgres, no Docker.

use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use axum::body::Body;
use axum::http::{header, HeaderMap, Request, StatusCode};
use axum::routing::{get, post};
use axum::Router;
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

use ideavalidator_web::auth;
use ideavalidator_web::config::Config;
use ideavalidator_web::crypto::Cipher;
use ideavalidator_web::db::InMemoryDb;
use ideavalidator_web::extract::CurrentAccount;
use ideavalidator_web::palgu::PalguHttp;
use ideavalidator_web::router::app;
use ideavalidator_web::runs::RunRegistry;
use ideavalidator_web::sse::SseHub;
use ideavalidator_web::state::{new_pending_map, AppState};
use ideavalidator_web::worker_proc::NoopSpawner;
use tokio::sync::Semaphore;

const KEY_HEX: &str = "1111111111111111111111111111111111111111111111111111111111111111";

struct FakePalgu {
    device: Value,
    token: Mutex<Vec<Value>>,
}

#[async_trait]
impl PalguHttp for FakePalgu {
    async fn post_json(&self, path: &str, _body: Value) -> Result<Value, String> {
        if path == "/auth/device/code" {
            Ok(self.device.clone())
        } else {
            Ok(self.token.lock().unwrap().remove(0))
        }
    }
    async fn get_json(&self, _path: &str, _bearer: &str) -> Result<Value, String> {
        Ok(Value::Null)
    }
}

fn device_ok() -> Value {
    json!({"ok": true, "body": {"device_code": "dc", "user_code": "WXYZ",
        "verification_uri": "https://palgu.ai/connect", "interval": 5, "expires_in": 600}})
}

fn token_success() -> Value {
    json!({"ok": true, "status": 200, "body": {"access_token": "k-1",
        "account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "pro"}}})
}

fn state_with(tokens: Vec<Value>) -> AppState {
    let cfg = Config::from(|k| (k == "TOKEN_ENC_KEY").then(|| KEY_HEX.to_string()));
    let palgu = FakePalgu {
        device: device_ok(),
        token: Mutex::new(tokens),
    };
    AppState {
        db: Arc::new(InMemoryDb::new()),
        palgu: Arc::new(palgu),
        cipher: Arc::new(Cipher::from_env_key(&cfg.token_enc_key).unwrap()),
        config: cfg,
        pending: new_pending_map(),
        spawner: Arc::new(NoopSpawner),
        hub: Arc::new(SseHub::new()),
        sem: Arc::new(Semaphore::new(3)),
        runs: RunRegistry::new(),
        mcp: ideavalidator_web::mcp::sessions::new_mcp_sessions(),
    }
}

fn post_req(uri: &str, body: Value) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri(uri)
        .header(header::CONTENT_TYPE, "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

async fn send(router: Router, req: Request<Body>) -> (StatusCode, HeaderMap, Value) {
    let resp = router.oneshot(req).await.unwrap();
    let status = resp.status();
    let headers = resp.headers().clone();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        headers,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

#[tokio::test]
async fn start_returns_user_code_and_poll_token() {
    let (status, _h, body) =
        send(app(state_with(vec![])), post_req("/auth/start", json!({}))).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["user_code"], "WXYZ");
    assert!(body["poll_token"].as_str().is_some_and(|s| !s.is_empty()));
}

#[tokio::test]
async fn poll_reports_pending_then_signs_in() {
    let st = state_with(vec![
        json!({"ok": false, "status": 400, "body": {"error": "authorization_pending"}}),
        token_success(),
    ]);
    let router = app(st);
    let (_s, _h, start) = send(router.clone(), post_req("/auth/start", json!({}))).await;
    let token = start["poll_token"].as_str().unwrap().to_string();

    let req = post_req("/auth/poll", json!({"poll_token": token}));
    let (_s, _h, pending) = send(router.clone(), req).await;
    assert_eq!(pending["status"], "pending");

    let req = post_req("/auth/poll", json!({"poll_token": token}));
    let (status, headers, done) = send(router, req).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(done["status"], "signed_in");
    assert_eq!(done["email"], "a@b.com");
    let cookie = headers.get(header::SET_COOKIE).unwrap().to_str().unwrap();
    assert!(cookie.contains("iv_session=") && cookie.contains("HttpOnly"));
}

#[tokio::test]
async fn poll_with_unknown_token_is_404() {
    let req = post_req("/auth/poll", json!({"poll_token": "nope"}));
    let (status, _h, body) = send(app(state_with(vec![])), req).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(body["status"], "unknown_poll_token");
}

async fn whoami(acc: CurrentAccount) -> String {
    acc.0
}

#[tokio::test]
async fn current_account_extractor_guards_and_reads_cookie() {
    let router = Router::new()
        .route("/auth/start", post(auth::start))
        .route("/auth/poll", post(auth::poll))
        .route("/whoami", get(whoami))
        .with_state(state_with(vec![token_success()]));

    // Sign in to obtain a real session cookie.
    let (_s, _h, start) = send(router.clone(), post_req("/auth/start", json!({}))).await;
    let token = start["poll_token"].as_str().unwrap().to_string();
    let (_s, headers, _b) = send(
        router.clone(),
        post_req("/auth/poll", json!({"poll_token": token})),
    )
    .await;
    let cookie = headers.get(header::SET_COOKIE).unwrap().to_str().unwrap();
    let session = cookie.split(';').next().unwrap().to_string();

    // No cookie -> 401.
    let bare = Request::builder()
        .uri("/whoami")
        .body(Body::empty())
        .unwrap();
    assert_eq!(send(router.clone(), bare).await.0, StatusCode::UNAUTHORIZED);

    // Valid cookie -> the account id.
    let req = Request::builder()
        .uri("/whoami")
        .header(header::COOKIE, session)
        .body(Body::empty())
        .unwrap();
    let (status, _h, _b) = send(router, req).await;
    assert_eq!(status, StatusCode::OK);
}
