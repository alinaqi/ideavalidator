//! Shared harness for the requirements-check route tests: a scripted [`ReqChecker`], app state, the
//! shared fixtures (`tests/fixtures/requirements_check/`) and a one-shot request helper.

use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use async_trait::async_trait;
use axum::body::Body;
use axum::http::{header, Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use tower::ServiceExt;

use ideavalidator_web::config::Config;
use ideavalidator_web::crypto::Cipher;
use ideavalidator_web::db::InMemoryDb;
use ideavalidator_web::palgu::PalguHttp;
use ideavalidator_web::reqcheck_proc::{CheckReply, ReqChecker};
use ideavalidator_web::router::app;
use ideavalidator_web::runs::RunRegistry;
use ideavalidator_web::sse::SseHub;
use ideavalidator_web::state::{new_pending_map, AppState};
use ideavalidator_web::worker_proc::NoopSpawner;
use tokio::sync::Semaphore;

const KEY_HEX: &str = "3333333333333333333333333333333333333333333333333333333333333333";
pub const URI: &str = "/api/v1/requirements/check";

struct NullPalgu;

#[async_trait]
impl PalguHttp for NullPalgu {
    async fn post_json(&self, _p: &str, _b: Value) -> Result<Value, String> {
        Ok(Value::Null)
    }
    async fn get_json(&self, _p: &str, _b: &str) -> Result<Value, String> {
        Ok(Value::Null)
    }
}

/// Replies with a scripted result (or sleeps past the deadline), recording the token it was given.
pub struct Scripted {
    pub reply: Result<CheckReply, String>,
    pub delay: Duration,
    pub seen: Mutex<Vec<String>>,
}

#[async_trait]
impl ReqChecker for Scripted {
    async fn check(&self, _body: Value, token: String) -> Result<CheckReply, String> {
        self.seen.lock().unwrap().push(token);
        tokio::time::sleep(self.delay).await;
        self.reply.clone()
    }
}

pub fn scripted(status: u16, body: Value) -> Arc<Scripted> {
    Arc::new(Scripted {
        reply: Ok(CheckReply { status, body }),
        delay: Duration::ZERO,
        seen: Mutex::new(vec![]),
    })
}

pub fn state(checker: Arc<dyn ReqChecker>) -> AppState {
    let cfg = Config::from(|k| match k {
        "TOKEN_ENC_KEY" => Some(KEY_HEX.to_string()),
        "REQ_CHECK_TIMEOUT_MS" => Some("200".to_string()),
        _ => None,
    });
    AppState {
        db: Arc::new(InMemoryDb::new()),
        palgu: Arc::new(NullPalgu),
        cipher: Arc::new(Cipher::from_env_key(KEY_HEX).unwrap()),
        config: cfg,
        pending: new_pending_map(),
        spawner: Arc::new(NoopSpawner),
        hub: Arc::new(SseHub::new()),
        sem: Arc::new(Semaphore::new(2)),
        runs: RunRegistry::new(),
        mcp: ideavalidator_web::mcp::sessions::new_mcp_sessions(),
        checker,
    }
}

pub fn fixture(name: &str) -> Value {
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../tests/fixtures/requirements_check")
        .join(name);
    serde_json::from_str(&std::fs::read_to_string(p).unwrap()).unwrap()
}

pub fn expand(mut body: Value) -> Value {
    if body["intent"] == "@LONG4001@" {
        body["intent"] = json!("x".repeat(4001));
    }
    if body["requirements"] == "@201REQS@" {
        let reqs: Vec<Value> = (0..201)
            .map(|i| json!({"id": format!("R-{i}"), "text": "x"}))
            .collect();
        body["requirements"] = json!(reqs);
    }
    body
}

pub fn request(body: &str, bearer: Option<&str>) -> Request<Body> {
    let mut b = Request::builder()
        .method("POST")
        .uri(URI)
        .header(header::CONTENT_TYPE, "application/json");
    if let Some(t) = bearer {
        b = b.header(header::AUTHORIZATION, format!("Bearer {t}"));
    }
    b.body(Body::from(body.to_string())).unwrap()
}

pub async fn call(st: AppState, req: Request<Body>) -> (StatusCode, Value) {
    let resp = app(st).oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}
