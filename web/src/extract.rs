//! `CurrentAccount` — an axum extractor that turns the session cookie into an `account_id`, or rejects
//! the request with 401. Handlers that need an authenticated caller take it as an argument (P3/P4 use it).

use async_trait::async_trait;
use axum::extract::FromRequestParts;
use axum::http::header::COOKIE;
use axum::http::request::Parts;
use axum::http::{HeaderMap, StatusCode};

use crate::session::parse_cookie;
use crate::state::AppState;

/// The authenticated caller's stable account id.
pub struct CurrentAccount(pub String);

/// Resolve the session cookie to an account id, or `None` — for browser pages that redirect rather than
/// return 401 (landing/dashboard). Never errors: a bad cookie or DB miss is simply "not signed in".
pub async fn account_from_headers(headers: &HeaderMap, st: &AppState) -> Option<String> {
    let token = headers
        .get(COOKIE)
        .and_then(|v| v.to_str().ok())
        .and_then(parse_cookie)?;
    st.db.session_account(&token).await.ok().flatten()
}

fn session_token(parts: &Parts) -> Option<String> {
    parts
        .headers
        .get(COOKIE)
        .and_then(|v| v.to_str().ok())
        .and_then(parse_cookie)
}

#[async_trait]
impl FromRequestParts<AppState> for CurrentAccount {
    type Rejection = StatusCode;

    async fn from_request_parts(parts: &mut Parts, st: &AppState) -> Result<Self, Self::Rejection> {
        let token = session_token(parts).ok_or(StatusCode::UNAUTHORIZED)?;
        let account = st
            .db
            .session_account(&token)
            .await
            .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
            .ok_or(StatusCode::UNAUTHORIZED)?;
        Ok(CurrentAccount(account))
    }
}
