//! End-to-end tests for the admin "delete a user" endpoint, driven through the real axum router with
//! an in-memory DB and the no-op worker spawner. The endpoint is gated by `ADMIN_TOKEN`: inert (404)
//! when unset, 401 without the matching `X-Admin-Token`, and a full account wipe when authorized.

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
const ADMIN: &str = "s3cret-admin";

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

fn state_with_admin(admin: &str) -> AppState {
    let admin = admin.to_string();
    let store = std::env::temp_dir()
        .join(format!("iv-admin-{}", std::process::id()))
        .to_string_lossy()
        .into_owned();
    let cfg = Config::from(move |k| match k {
        "TOKEN_ENC_KEY" => Some(KEY_HEX.to_string()),
        "IV_STORE" => Some(store.clone()),
        "ADMIN_TOKEN" => (!admin.is_empty()).then(|| admin.clone()),
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

fn del(email: &str, token: Option<&str>) -> Request<Body> {
    let mut b = Request::builder()
        .method("POST")
        .uri("/admin/users/delete")
        .header(header::CONTENT_TYPE, "application/json");
    if let Some(t) = token {
        b = b.header("x-admin-token", t);
    }
    b.body(Body::from(json!({ "email": email }).to_string()))
        .unwrap()
}

async fn sign_in(router: &Router) -> String {
    let (_s, start) = send(
        router.clone(),
        Request::builder()
            .method("POST")
            .uri("/auth/start")
            .header(header::CONTENT_TYPE, "application/json")
            .body(Body::from("{}"))
            .unwrap(),
    )
    .await;
    let token = start["poll_token"].as_str().unwrap().to_string();
    let resp = router
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/auth/poll")
                .header(header::CONTENT_TYPE, "application/json")
                .body(Body::from(json!({ "poll_token": token }).to_string()))
                .unwrap(),
        )
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
async fn delete_is_404_when_admin_token_unset() {
    let (status, _) = send(app(state_with_admin("")), del("a@b.com", Some("anything"))).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn delete_requires_the_admin_token() {
    let st = state_with_admin(ADMIN);
    let (no_tok, _) = send(app(st.clone()), del("a@b.com", None)).await;
    assert_eq!(no_tok, StatusCode::UNAUTHORIZED);
    let (bad_tok, _) = send(app(st), del("a@b.com", Some("wrong"))).await;
    assert_eq!(bad_tok, StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn delete_wipes_the_account_and_its_runs() {
    let st = state_with_admin(ADMIN);
    let router = app(st.clone());
    let cookie = sign_in(&router).await;
    // create a run so the account has data
    let _ = send(
        router.clone(),
        Request::builder()
            .method("POST")
            .uri("/api/runs")
            .header(header::CONTENT_TYPE, "application/json")
            .header(header::COOKIE, &cookie)
            .body(Body::from(json!({"pitch": "an idea"}).to_string()))
            .unwrap(),
    )
    .await;
    let account = ideavalidator_web::account::account_id("a@b.com");
    assert!(st.db.get_user(&account).await.unwrap().is_some());

    let (status, body) = send(router, del("a@b.com", Some(ADMIN))).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["account_id"], account);
    assert!(st.db.get_user(&account).await.unwrap().is_none());
    assert!(st.db.list_runs(&account).await.unwrap().is_empty());
}
