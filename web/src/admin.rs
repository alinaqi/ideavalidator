//! Admin endpoints, gated by the `ADMIN_TOKEN` shared secret. The feature is OFF unless the secret is
//! set (every call then 404s, so the route is invisible); when set, each call must carry a matching
//! `X-Admin-Token` header, constant-time compared. The one action today is a full account wipe used to
//! reset a test user to zero. The secret is read from config (env only) and is never logged.

use std::path::Path;

use axum::body::Bytes;
use axum::extract::State;
use axum::http::header::HeaderMap;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::Deserialize;
use serde_json::json;

use crate::account::account_id;
use crate::jobs::JobManager;
use crate::state::AppState;

#[derive(Deserialize)]
pub struct DeleteReq {
    pub email: String,
}

/// Length-checked constant-time comparison, so a wrong token leaks no timing signal.
fn ct_eq(a: &[u8], b: &[u8]) -> bool {
    a.len() == b.len() && a.iter().zip(b).fold(0u8, |acc, (x, y)| acc | (x ^ y)) == 0
}

/// Gate: 404 when the feature is off (no secret), 401 when the header is missing or wrong.
fn authorize(st: &AppState, headers: &HeaderMap) -> Result<(), StatusCode> {
    if st.config.admin_token.is_empty() {
        return Err(StatusCode::NOT_FOUND);
    }
    let provided = headers
        .get("x-admin-token")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    match ct_eq(provided.as_bytes(), st.config.admin_token.as_bytes()) {
        true => Ok(()),
        false => Err(StatusCode::UNAUTHORIZED),
    }
}

/// Cancel the account's in-flight runs, delete its rows, and remove its on-disk run files.
async fn purge(st: &AppState, account: &str) -> Result<u64, String> {
    if let Ok(runs) = st.db.list_runs(account).await {
        let jm = JobManager::new(st.clone());
        for r in runs {
            jm.request_cancel(&r.id);
        }
    }
    let n = st.db.delete_account(account).await?;
    let _ = std::fs::remove_dir_all(Path::new(&st.config.store_dir).join(account));
    Ok(n)
}

/// `POST /admin/users/delete {email}` — wipe an account (db rows + on-disk runs) so it restarts fresh.
pub async fn delete_user(State(st): State<AppState>, headers: HeaderMap, body: Bytes) -> Response {
    if let Err(code) = authorize(&st, &headers) {
        return code.into_response();
    }
    let email = match serde_json::from_slice::<DeleteReq>(&body) {
        Ok(r) if !r.email.is_empty() => r.email,
        _ => return StatusCode::BAD_REQUEST.into_response(),
    };
    let account = account_id(&email);
    match purge(&st, &account).await {
        Ok(n) => Json(json!({ "account_id": account, "runs_deleted": n })).into_response(),
        Err(_) => StatusCode::INTERNAL_SERVER_ERROR.into_response(),
    }
}

#[cfg(test)]
mod tests {
    use super::ct_eq;

    #[test]
    fn ct_eq_matches_only_identical_bytes() {
        assert!(ct_eq(b"secret", b"secret"));
        assert!(!ct_eq(b"secret", b"secreT"));
        assert!(!ct_eq(b"secret", b"secret-longer"));
        assert!(!ct_eq(b"", b"x"));
        assert!(ct_eq(b"", b""));
    }
}
