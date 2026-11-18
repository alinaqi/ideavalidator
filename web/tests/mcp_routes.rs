//! End-to-end tests for the hosted MCP endpoint `/mcp`, driven through the real axum router with an
//! in-memory DB, a scripted Palgu that signs in on the first poll, and the no-op worker spawner. No
//! network, no Postgres, no Python — the required gate runs these as-is. Covers the JSON-RPC handshake,
//! tools/list, notifications, an unknown method, and a full signed-in tools/call flow.

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

const KEY_HEX: &str = "4444444444444444444444444444444444444444444444444444444444444444";
const SESS: &str = "test-sess";

struct SigningPalgu {
    tokens: Mutex<Vec<Value>>,
}

#[async_trait]
impl PalguHttp for SigningPalgu {
    async fn post_json(&self, path: &str, _body: Value) -> Result<Value, String> {
        if path == "/auth/device/code" {
            Ok(
                json!({"ok": true, "body": {"device_code": "dc", "user_code": "WXYZ",
                "verification_uri": "https://www.palgu.ai/connect", "interval": 0, "expires_in": 600}}),
            )
        } else {
            Ok(self.tokens.lock().unwrap().remove(0))
        }
    }
    async fn get_json(&self, _path: &str, _bearer: &str) -> Result<Value, String> {
        Ok(json!({"ok": true, "body": {"account": {"email": "a@b.com"},
            "org": {"name": "Acme", "plan": "pro"}}}))
    }
}

fn token_success() -> Value {
    json!({"ok": true, "status": 200, "body": {"access_token": "k-1",
        "account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "pro"}}})
}

fn test_state() -> AppState {
    let store = std::env::temp_dir()
        .join(format!("iv-mcp-it-{}", std::process::id()))
        .to_string_lossy()
        .into_owned();
    let cfg = Config::from(move |k| match k {
        "TOKEN_ENC_KEY" => Some(KEY_HEX.to_string()),
        "IV_STORE" => Some(store.clone()),
        _ => None,
    });
    AppState {
        db: Arc::new(InMemoryDb::new()),
        palgu: Arc::new(SigningPalgu {
            tokens: Mutex::new(vec![token_success()]),
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

fn rpc(method: &str, params: Value) -> Value {
    json!({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
}

fn post(body: Value, session: Option<&str>) -> Request<Body> {
    let mut b = Request::builder()
        .method("POST")
        .uri("/mcp")
        .header(header::CONTENT_TYPE, "application/json");
    if let Some(s) = session {
        b = b.header("mcp-session-id", s);
    }
    b.body(Body::from(body.to_string())).unwrap()
}

async fn send(router: &Router, req: Request<Body>) -> (StatusCode, Value) {
    let resp = router.clone().oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

async fn call(router: &Router, name: &str, args: Value) -> Value {
    let (_s, v) = send(
        router,
        post(
            rpc("tools/call", json!({"name": name, "arguments": args})),
            Some(SESS),
        ),
    )
    .await;
    v
}

fn text_of(result: &Value) -> String {
    result["result"]["content"][0]["text"]
        .as_str()
        .unwrap()
        .to_string()
}

#[tokio::test]
async fn initialize_returns_handshake_and_session_header() {
    let router = app(test_state());
    let req = post(
        rpc("initialize", json!({"protocolVersion": "2025-06-18"})),
        None,
    );
    let resp = router.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    assert!(resp.headers().get("mcp-session-id").is_some());
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    let v: Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(v["result"]["serverInfo"]["name"], "ideavalidator");
    assert_eq!(v["result"]["protocolVersion"], "2025-06-18");
}

#[tokio::test]
async fn tools_list_exposes_seven_tools() {
    let router = app(test_state());
    let (status, v) = send(&router, post(rpc("tools/list", json!({})), Some(SESS))).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(v["result"]["tools"].as_array().unwrap().len(), 7);
}

#[tokio::test]
async fn notification_is_accepted_without_a_body() {
    let router = app(test_state());
    let notif = json!({"jsonrpc": "2.0", "method": "notifications/initialized"});
    let resp = router.oneshot(post(notif, Some(SESS))).await.unwrap();
    assert_eq!(resp.status(), StatusCode::ACCEPTED);
}

#[tokio::test]
async fn unknown_method_is_a_jsonrpc_error() {
    let router = app(test_state());
    let (_s, v) = send(&router, post(rpc("does/not/exist", json!({})), Some(SESS))).await;
    assert_eq!(v["error"]["code"], -32601);
}

#[tokio::test]
async fn get_requests_are_not_allowed() {
    let router = app(test_state());
    let req = Request::builder()
        .method("GET")
        .uri("/mcp")
        .body(Body::empty())
        .unwrap();
    let resp = router.oneshot(req).await.unwrap();
    assert_eq!(resp.status(), StatusCode::METHOD_NOT_ALLOWED);
}

async fn wait_until_signed_in(router: &Router) {
    for _ in 0..100 {
        let out = call(router, "palgu_status", json!({})).await;
        if text_of(&out).contains("signed in as a@b.com") {
            return;
        }
        tokio::time::sleep(std::time::Duration::from_millis(5)).await;
    }
    panic!("never signed in");
}

#[tokio::test]
async fn full_signed_in_flow_validate_list_status() {
    let router = app(test_state());
    let login = call(&router, "palgu_login", json!({})).await;
    assert!(text_of(&login).contains("approve code WXYZ"));
    wait_until_signed_in(&router).await;

    let started = text_of(
        &call(
            &router,
            "validate_idea",
            json!({"pitch": "an AI tutor for nurses"}),
        )
        .await,
    );
    assert!(started.starts_with("Validation started for 'an-ai-tutor-for-nurses'. run_id: "));
    let run_id = started
        .split("run_id: ")
        .nth(1)
        .unwrap()
        .split('\n')
        .next()
        .unwrap()
        .to_string();

    let listed = text_of(&call(&router, "list_runs", json!({})).await);
    assert!(listed.contains(&run_id));

    let status = call(&router, "get_status", json!({"run_id": run_id})).await;
    assert_eq!(status["result"]["structuredContent"]["total"], 10);
}
