//! `POST /api/v1/requirements/check` (contract v1, srooter#2785, ADR 0014). Authenticates with the
//! caller's short-lived Palgu key (Bearer), validates the body (422), runs the Python worker through
//! [`ReqChecker`] under a hard deadline (503 on timeout) and relays its answer. A reply that is not a
//! well-formed verdict becomes 503: this route never returns `ok` for a check that did not run.

use std::time::{Duration, Instant};

use axum::body::Bytes;
use axum::extract::State;
use axum::http::{HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde_json::{json, Value};

use crate::reqcheck_input::{log_counts, validate};
use crate::reqcheck_proc::CheckReply;
use crate::state::AppState;

const RELAYED: [u16; 5] = [200, 401, 402, 422, 503];

fn error(status: StatusCode, code: &str, message: &str) -> Response {
    let body = json!({"error": {"code": code, "message": message}});
    (status, Json(body)).into_response()
}

fn bearer(headers: &HeaderMap) -> Option<String> {
    let raw = headers.get("authorization")?.to_str().ok()?;
    let token = raw.strip_prefix("Bearer ")?.trim();
    (!token.is_empty()).then(|| token.to_string())
}

fn well_formed(body: &Value) -> bool {
    let verdict = body["verdict"].as_str().unwrap_or("");
    ["ok", "questions", "blocked"].contains(&verdict)
        && body["findings"].is_array()
        && body["contract"] == 1
}

fn relay(reply: CheckReply, started: Instant) -> Response {
    let ok = reply.status == 200 && well_formed(&reply.body);
    if !(ok || reply.status != 200 && RELAYED.contains(&reply.status)) {
        eprintln!("reqcheck: bad worker reply status={}", reply.status);
        return error(
            StatusCode::SERVICE_UNAVAILABLE,
            "check_unavailable",
            "the check did not run",
        );
    }
    let mut body = reply.body;
    if ok {
        body["duration_ms"] = json!(started.elapsed().as_millis() as u64);
    }
    let status = StatusCode::from_u16(reply.status).unwrap_or(StatusCode::SERVICE_UNAVAILABLE);
    (status, Json(body)).into_response()
}

pub async fn check(State(st): State<AppState>, headers: HeaderMap, raw: Bytes) -> Response {
    let started = Instant::now();
    let Some(token) = bearer(&headers) else {
        return error(
            StatusCode::UNAUTHORIZED,
            "unauthorized",
            "missing Bearer Palgu key",
        );
    };
    let body: Value = match serde_json::from_slice(&raw) {
        Ok(v) => v,
        Err(_) => return error(StatusCode::UNPROCESSABLE_ENTITY, "invalid_body", "not JSON"),
    };
    if let Err(why) = validate(&body) {
        return error(StatusCode::UNPROCESSABLE_ENTITY, "invalid_body", &why);
    }
    eprintln!("reqcheck: start {}", log_counts(&body));
    let deadline = Duration::from_millis(st.config.req_check_timeout_ms);
    match tokio::time::timeout(deadline, st.checker.check(body, token)).await {
        Ok(Ok(reply)) => relay(reply, started),
        Ok(Err(why)) => {
            eprintln!("reqcheck: worker failed: {why}");
            error(
                StatusCode::SERVICE_UNAVAILABLE,
                "check_unavailable",
                "the check did not run",
            )
        }
        Err(_) => {
            eprintln!("reqcheck: timed out after {} ms", deadline.as_millis());
            error(
                StatusCode::SERVICE_UNAVAILABLE,
                "check_timeout",
                "the check timed out",
            )
        }
    }
}
