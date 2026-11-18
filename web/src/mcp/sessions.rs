//! MCP session -> account mapping. Parity with `server/keystore.py`: the hosted MCP keys a signed-in
//! Palgu account by the MCP session id. The improvement over `server/` (per ADR 0013) is that the user's
//! encrypted key is persisted in Postgres (`users`), so history survives a restart; this in-memory map
//! only resolves the live session to its account id. Status text matches `pipeline/palgu_text.py`.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use crate::palgu_flow::{fetch_me, Me};
use crate::state::AppState;

const PALGU_BILLING: &str = "https://www.palgu.ai/billing";

/// `session_id -> account_id` for live MCP sessions (the key itself lives encrypted in `users`).
pub type McpSessions = Arc<Mutex<HashMap<String, String>>>;

/// A fresh, empty session map (fields on `AppState` are public, so callers build the literal).
pub fn new_mcp_sessions() -> McpSessions {
    Arc::new(Mutex::new(HashMap::new()))
}

/// Bind an MCP session to the account it signed in as.
pub fn map_session(st: &AppState, session_id: &str, account_id: &str) {
    st.mcp
        .lock()
        .unwrap()
        .insert(session_id.to_string(), account_id.to_string());
}

/// The account bound to this MCP session, if it is signed in.
pub fn account_for(st: &AppState, session_id: &str) -> Option<String> {
    st.mcp.lock().unwrap().get(session_id).cloned()
}

fn not_signed_in() -> String {
    "Palgu: not signed in. Run `palgu login` to sign up or sign in from here.".to_string()
}

fn signed_in_text(me: &Me) -> String {
    format!(
        "Palgu: signed in as {} ({}, plan {}) · upgrade: {PALGU_BILLING}",
        me.email, me.org, me.plan,
    )
}

/// `palgu_status` text: live `/me` lookup for the session's account, or the not-signed-in line.
pub async fn status(st: &AppState, session_id: &str) -> String {
    let Some(account) = account_for(st, session_id) else {
        return not_signed_in();
    };
    match me_for_account(st, &account).await {
        Some(me) => signed_in_text(&me),
        None => not_signed_in(),
    }
}

async fn me_for_account(st: &AppState, account_id: &str) -> Option<Me> {
    let user = st.db.get_user(account_id).await.ok()??;
    let key = st.cipher.decrypt(&user.enc_token).ok()?;
    fetch_me(st.palgu.as_ref(), &key).await.ok()
}

#[cfg(test)]
#[path = "sessions_tests.rs"]
mod tests;
