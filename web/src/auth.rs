//! JSON auth endpoints for the Palgu device flow. Handlers stay thin: pure logic lives in `palgu`,
//! `crypto`, `session` and `db`. No HTML here — the UI arrives in P3.

use axum::extract::State;
use axum::http::header::{HeaderMap, COOKIE, SET_COOKIE};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::account::account_id;
use crate::db::{self, Session, User};
use crate::palgu::{token_step, Account, TokenStep};
use crate::palgu_flow::{start_device, token_body};
use crate::session::{self, build_cookie, clear_cookie, parse_cookie, SESSION_MAX_AGE};
use crate::state::{AppState, Pending};

#[derive(Deserialize)]
pub struct PollReq {
    pub poll_token: String,
}

fn json_status(code: StatusCode, body: Value) -> Response {
    (code, Json(body)).into_response()
}

fn cookie_token(headers: &HeaderMap) -> Option<String> {
    headers
        .get(COOKIE)
        .and_then(|v| v.to_str().ok())
        .and_then(parse_cookie)
}

/// `POST /auth/start`: begin a device flow and hand back the user code + a poll token.
pub async fn start(State(st): State<AppState>) -> Response {
    let device = match start_device(st.palgu.as_ref()).await {
        Ok(d) => d,
        Err(_) => {
            return json_status(
                StatusCode::BAD_GATEWAY,
                json!({"error": "could not start sign-in"}),
            )
        }
    };
    let poll_token = session::new_token();
    st.pending
        .lock()
        .unwrap()
        .insert(poll_token.clone(), Pending::from(&device));
    Json(json!({
        "user_code": device.user_code,
        "verification_uri": device.verification_uri,
        "verification_uri_complete": device.verification_uri_complete,
        "poll_token": poll_token,
    }))
    .into_response()
}

fn take_pending(st: &AppState, token: &str) -> Option<Pending> {
    st.pending.lock().unwrap().get(token).cloned()
}

/// `POST /auth/poll`: advance the device poll once. On success, signs in and sets the session cookie.
pub async fn poll(State(st): State<AppState>, Json(req): Json<PollReq>) -> Response {
    match take_pending(&st, &req.poll_token) {
        Some(pending) => advance(&st, &req.poll_token, pending).await,
        None => json_status(
            StatusCode::NOT_FOUND,
            json!({"status": "unknown_poll_token"}),
        ),
    }
}

async fn advance(st: &AppState, poll_token: &str, pending: Pending) -> Response {
    let res = match st
        .palgu
        .post_json("/auth/token", token_body(&pending.device_code))
        .await
    {
        Ok(v) => v,
        Err(_) => return json_status(StatusCode::BAD_GATEWAY, json!({"status": "error"})),
    };
    match token_step(&res, pending.interval) {
        TokenStep::Wait(_) => Json(json!({"status": "pending"})).into_response(),
        TokenStep::Stop(reason) => json_status(
            StatusCode::OK,
            json!({"status": "stopped", "reason": reason}),
        ),
        TokenStep::Ok(acc) => finish(st, poll_token, acc).await,
    }
}

async fn finish(st: &AppState, poll_token: &str, acc: Account) -> Response {
    match persist(st, &acc).await {
        Ok(cookie) => {
            st.pending.lock().unwrap().remove(poll_token);
            let body = Json(json!({"status": "signed_in", "email": acc.email}));
            ([(SET_COOKIE, cookie)], body).into_response()
        }
        Err(_) => json_status(
            StatusCode::INTERNAL_SERVER_ERROR,
            json!({"status": "error"}),
        ),
    }
}

async fn persist(st: &AppState, acc: &Account) -> Result<String, String> {
    let account = account_id(&acc.email);
    let enc_token = st.cipher.encrypt(&acc.key)?;
    let user = User {
        account_id: account.clone(),
        email: acc.email.clone(),
        plan: acc.plan.clone(),
        enc_token,
    };
    st.db.upsert_user(user).await?;
    let token = session::new_token();
    let expires_at = db::now_unix() + SESSION_MAX_AGE;
    st.db
        .create_session(Session {
            token: token.clone(),
            account_id: account,
            expires_at,
        })
        .await?;
    Ok(build_cookie(&token, SESSION_MAX_AGE))
}

/// `POST /auth/logout`: drop the session (if any) and clear the cookie.
pub async fn logout(State(st): State<AppState>, headers: HeaderMap) -> Response {
    if let Some(token) = cookie_token(&headers) {
        let _ = st.db.delete_session(&token).await;
    }
    (
        [(SET_COOKIE, clear_cookie())],
        Json(json!({"status": "signed_out"})),
    )
        .into_response()
}
