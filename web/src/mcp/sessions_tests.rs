//! Tests for the MCP session map and `palgu_status` text (parity with `pipeline/palgu_text.py`).

use super::*;
use crate::db::User;
use crate::mcp::testsupport::{signing_in, state_with};

#[tokio::test]
async fn status_is_not_signed_in_without_a_binding() {
    let st = state_with(signing_in());
    assert_eq!(
        status(&st, "sess").await,
        "Palgu: not signed in. Run `palgu login` to sign up or sign in from here."
    );
}

#[tokio::test]
async fn status_reports_account_org_and_plan_when_signed_in() {
    let st = state_with(signing_in());
    let enc = st.cipher.encrypt("k-1").unwrap();
    st.db
        .upsert_user(User {
            account_id: "acc".into(),
            email: "a@b.com".into(),
            plan: "pro".into(),
            enc_token: enc,
        })
        .await
        .unwrap();
    map_session(&st, "sess", "acc");
    assert_eq!(
        status(&st, "sess").await,
        "Palgu: signed in as a@b.com (Acme, plan pro) · upgrade: https://www.palgu.ai/billing"
    );
}

#[test]
fn map_and_account_for_round_trip() {
    let st = state_with(signing_in());
    assert_eq!(account_for(&st, "s1"), None);
    map_session(&st, "s1", "acc-1");
    assert_eq!(account_for(&st, "s1").as_deref(), Some("acc-1"));
}
