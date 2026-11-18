//! Tests for MCP `palgu_login`: the approve text, the could-not-start path, and the background poll
//! persisting the account + binding the session — all without network or real sleeps.

use super::*;
use crate::mcp::sessions::account_for;
use crate::mcp::testsupport::{device_ok, me_ok, signing_in, state_with, ScriptedPalgu};
use serde_json::json;
use std::sync::Mutex;

#[test]
fn start_text_matches_python_wording() {
    let start = DeviceStart {
        device_code: "dc".into(),
        user_code: "WXYZ".into(),
        verification_uri: "https://www.palgu.ai/connect".into(),
        verification_uri_complete: String::new(),
        interval: 5,
        expires_in: 600,
    };
    assert_eq!(
        start_text(&start),
        "Open https://www.palgu.ai/connect?code=WXYZ and approve code WXYZ (new to Palgu? sign up \
there). The code expires in 10 minutes; this run picks up the key once you approve."
    );
}

#[tokio::test]
async fn login_without_device_code_reports_could_not_start() {
    let palgu = ScriptedPalgu {
        device: json!({"ok": true, "body": {}}),
        tokens: Mutex::new(vec![]),
        me: me_ok(),
    };
    let st = state_with(palgu);
    assert_eq!(
        login(&st, "sess").await,
        "Palgu sign-in could not start; try again."
    );
}

#[tokio::test]
async fn login_returns_the_approve_text_on_start() {
    let st = state_with(signing_in());
    let text = login(&st, "sess").await;
    assert!(text.contains("approve code WXYZ"));
}

#[tokio::test]
async fn poll_persists_the_account_and_binds_the_session() {
    let st = state_with(signing_in());
    let start = DeviceStart {
        device_code: "dc".into(),
        user_code: "WXYZ".into(),
        verification_uri: "https://www.palgu.ai/connect".into(),
        verification_uri_complete: String::new(),
        interval: 0,
        expires_in: 600,
    };
    assert!(run_login_poll(&st, "sess", start).await);
    // account_id("a@b.com") == "fb98d44ad7501a95"
    assert_eq!(
        account_for(&st, "sess").as_deref(),
        Some("fb98d44ad7501a95")
    );
    let user = st.db.get_user("fb98d44ad7501a95").await.unwrap().unwrap();
    assert_eq!(st.cipher.decrypt(&user.enc_token).unwrap(), "k-1");
}

#[tokio::test]
async fn poll_that_is_denied_does_not_sign_in() {
    let palgu = ScriptedPalgu {
        device: device_ok(),
        tokens: Mutex::new(vec![
            json!({"ok": false, "status": 400, "body": {"error": "access_denied"}}),
        ]),
        me: me_ok(),
    };
    let st = state_with(palgu);
    let start = DeviceStart {
        device_code: "dc".into(),
        user_code: "WXYZ".into(),
        verification_uri: "x".into(),
        verification_uri_complete: String::new(),
        interval: 0,
        expires_in: 600,
    };
    assert!(!run_login_poll(&st, "sess", start).await);
    assert_eq!(account_for(&st, "sess"), None);
}
