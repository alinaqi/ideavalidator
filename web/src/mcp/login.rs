//! MCP `palgu_login`: start the Palgu device flow, hand back the approve-at-palgu.ai text immediately,
//! and poll for approval in the background. On approval the minted key is encrypted and persisted to
//! `users` (so history survives a restart) and the MCP session is bound to the account. Mirrors
//! `server/palgu_session.py`, reusing the pure state machine in [`crate::palgu`]. The poll loop
//! ([`run_login_poll`]) is split out so it is awaited directly in tests — no background race, no network.

use std::time::Duration;

use crate::account::account_id;
use crate::db::User;
use crate::mcp::sessions::map_session;
use crate::palgu::{token_step, Account, DeviceStart, TokenStep};
use crate::palgu_flow::{start_device, token_body};
use crate::state::AppState;

const PALGU_WEB: &str = "https://www.palgu.ai";
const START_FAILED: &str = "Palgu sign-in could not start; try again.";

/// The approve-at-palgu.ai instructions (parity with `pipeline/palgu_text.py::start_text`).
pub fn start_text(start: &DeviceStart) -> String {
    let minutes = (start.expires_in as f64 / 60.0).round() as u64;
    let code = &start.user_code;
    format!(
        "Open {PALGU_WEB}/connect?code={code} and approve code {code} (new to Palgu? sign up \
there). The code expires in {minutes} minutes; this run picks up the key once you approve."
    )
}

/// Begin a sign-in: return the approve text and poll in the background, or a could-not-start message.
pub async fn login(st: &AppState, session_id: &str) -> String {
    match start_device(st.palgu.as_ref()).await {
        Ok(start) => spawn_poll(st, session_id, start),
        Err(_) => START_FAILED.to_string(),
    }
}

fn spawn_poll(st: &AppState, session_id: &str, start: DeviceStart) -> String {
    let text = start_text(&start);
    let (st, sid) = (st.clone(), session_id.to_string());
    tokio::spawn(async move {
        run_login_poll(&st, &sid, start).await;
    });
    text
}

async fn poll_once(st: &AppState, device_code: &str, interval: u64) -> TokenStep {
    match st
        .palgu
        .post_json("/auth/token", token_body(device_code))
        .await
    {
        Ok(res) => token_step(&res, interval),
        Err(_) => TokenStep::Stop("Palgu could not be reached".into()),
    }
}

/// Poll `/auth/token` until approval, denial or expiry; on approval persist + bind. Returns success.
pub async fn run_login_poll(st: &AppState, session_id: &str, start: DeviceStart) -> bool {
    let (mut interval, mut waited) = (start.interval, 0u64);
    while waited < start.expires_in {
        match poll_once(st, &start.device_code, interval).await {
            TokenStep::Ok(acc) => return finish(st, session_id, &acc).await,
            TokenStep::Stop(_) => return false,
            TokenStep::Wait(next) => {
                interval = next;
                tokio::time::sleep(Duration::from_secs(interval)).await;
                waited += interval;
            }
        }
    }
    false
}

async fn finish(st: &AppState, session_id: &str, acc: &Account) -> bool {
    match persist(st, acc).await {
        Ok(account) => {
            map_session(st, session_id, &account);
            true
        }
        Err(_) => false,
    }
}

async fn persist(st: &AppState, acc: &Account) -> Result<String, String> {
    let account = account_id(&acc.email);
    let enc_token = st.cipher.encrypt(&acc.key)?;
    st.db
        .upsert_user(User {
            account_id: account.clone(),
            email: acc.email.clone(),
            plan: acc.plan.clone(),
            enc_token,
        })
        .await?;
    Ok(account)
}

#[cfg(test)]
#[path = "login_tests.rs"]
mod tests;
