//! Contract-v1 tests for `POST /api/v1/requirements/check` (srooter#2785, ADR 0014), driven through the
//! real router with a scripted checker. The request fixtures are shared with the Python tests
//! (`tests/fixtures/requirements_check/`). No network, no Python, no Postgres.

mod support;

use std::sync::{Arc, Mutex};
use std::time::Duration;

use axum::http::StatusCode;
use serde_json::{json, Value};

use ideavalidator_web::reqcheck_proc::CheckReply;
use support::{call, expand, fixture, request, scripted, state, Scripted};

fn ok_body(verdict: &str) -> Value {
    json!({"verdict": verdict, "findings": [], "summary": "s", "model": "gemini-3.8-flash",
           "duration_ms": 5, "contract": 1})
}

#[tokio::test]
async fn each_verdict_is_relayed_with_the_callers_key() {
    for verdict in ["ok", "questions", "blocked"] {
        let checker = scripted(200, ok_body(verdict));
        let body = fixture("request_wrong.json").to_string();
        let (status, got) = call(
            state(checker.clone()),
            request(&body, Some("srt_short_lived")),
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(got["verdict"], verdict);
        assert_eq!(got["contract"], 1);
        assert!(got["duration_ms"].as_u64().is_some());
        assert_eq!(*checker.seen.lock().unwrap(), vec!["srt_short_lived"]);
    }
}

#[tokio::test]
async fn missing_or_malformed_bearer_is_401_without_running() {
    let body = fixture("request_ok.json").to_string();
    for bearer in [None, Some("")] {
        let checker = scripted(200, ok_body("ok"));
        let (status, got) = call(state(checker.clone()), request(&body, bearer)).await;
        assert_eq!(status, StatusCode::UNAUTHORIZED);
        assert_eq!(got["error"]["code"], "unauthorized");
        assert!(checker.seen.lock().unwrap().is_empty());
    }
}

#[tokio::test]
async fn invalid_bodies_are_422_without_running() {
    let cases = fixture("invalid_bodies.json");
    let mut bodies: Vec<(String, String)> = cases
        .as_array()
        .unwrap()
        .iter()
        .map(|c| (c["name"].to_string(), expand(c["body"].clone()).to_string()))
        .collect();
    bodies.push(("not_json".into(), "{nope".into()));
    for (name, body) in bodies {
        let checker = scripted(200, ok_body("ok"));
        let (status, got) = call(state(checker.clone()), request(&body, Some("k"))).await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY, "{name}");
        assert_eq!(got["error"]["code"], "invalid_body", "{name}");
        assert!(checker.seen.lock().unwrap().is_empty(), "{name}");
    }
}

#[tokio::test]
async fn palgu_rejection_and_budget_pass_through() {
    let body = fixture("request_ok.json").to_string();
    let budget = json!({"error": {"code": "budget_exceeded", "message": "top up"}});
    let cases = [
        (
            401,
            json!({"error": {"code": "unauthorized", "message": "x"}}),
        ),
        (402, budget.clone()),
        (
            422,
            json!({"error": {"code": "invalid_body", "message": "x"}}),
        ),
        (
            503,
            json!({"error": {"code": "palgu_unavailable", "message": "x"}}),
        ),
    ];
    for (code, reply) in cases {
        let (status, got) = call(
            state(scripted(code, reply.clone())),
            request(&body, Some("k")),
        )
        .await;
        assert_eq!(status.as_u16(), code);
        assert_eq!(got, reply);
    }
}

#[tokio::test]
async fn timeout_is_503_never_ok() {
    let checker = Arc::new(Scripted {
        reply: Ok(CheckReply {
            status: 200,
            body: ok_body("ok"),
        }),
        delay: Duration::from_secs(5),
        seen: Mutex::new(vec![]),
    });
    let body = fixture("request_ok.json").to_string();
    let (status, got) = call(state(checker), request(&body, Some("k"))).await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE);
    assert_eq!(got["error"]["code"], "check_timeout");
    assert!(got.get("verdict").is_none());
}

#[tokio::test]
async fn worker_failure_or_bad_reply_is_503() {
    let body = fixture("request_ok.json").to_string();
    let failing = Arc::new(Scripted {
        reply: Err("spawn failed".into()),
        delay: Duration::ZERO,
        seen: Mutex::new(vec![]),
    });
    let bad_replies = [
        scripted(200, json!({"findings": []})),
        scripted(200, json!({"verdict": "fine", "contract": 1})),
        scripted(500, json!({})),
    ];
    let mut checkers: Vec<Arc<Scripted>> = bad_replies.into();
    checkers.push(failing);
    for checker in checkers {
        let (status, got) = call(state(checker), request(&body, Some("k"))).await;
        assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE);
        assert_eq!(got["error"]["code"], "check_unavailable");
        assert!(got.get("verdict").is_none());
    }
}
