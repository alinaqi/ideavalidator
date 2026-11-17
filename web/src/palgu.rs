//! Native Palgu device-code sign-in (RFC 8628), ported from `pipeline/palgu.py`. This module holds the
//! injectable HTTP trait, the response types, and the PURE `token_step` state machine (unit-tested with
//! scripted JSON). Request building, the network flow and the reqwest impl live in sibling modules.

use async_trait::async_trait;
use serde_json::Value;

pub const CLIENT_ID: &str = "ideavalidator";
pub const CLIENT_VERSION: &str = "0.1.0";
const DEVICE_GRANT: &str = "urn:ietf:params:oauth:grant-type:device_code";

/// Injectable transport. `post_json`/`get_json` return the `{ok,status,body}` envelope as JSON,
/// mirroring `pipeline/palgu_run.py::_Http`; an `Err` means the request could not be made at all.
#[async_trait]
pub trait PalguHttp: Send + Sync {
    async fn post_json(&self, path: &str, body: Value) -> Result<Value, String>;
    async fn get_json(&self, path: &str, bearer: &str) -> Result<Value, String>;
}

/// What `POST /auth/device/code` hands back: the user-facing code and where to approve it.
#[derive(Debug, Clone, PartialEq)]
pub struct DeviceStart {
    pub device_code: String,
    pub user_code: String,
    pub verification_uri: String,
    pub interval: u64,
    pub expires_in: u64,
}

/// A signed-in Palgu account: the minted key plus who it belongs to.
#[derive(Debug, Clone, PartialEq)]
pub struct Account {
    pub key: String,
    pub email: String,
    pub org: String,
    pub plan: String,
}

/// One answer from `POST /auth/token`.
#[derive(Debug, Clone, PartialEq)]
pub enum TokenStep {
    Wait(u64),
    Stop(String),
    Ok(Account),
}

pub(crate) fn device_grant() -> &'static str {
    DEVICE_GRANT
}

fn stop_reason(err: Option<&str>, status: Option<i64>) -> String {
    match err {
        Some("expired_token") => "the code expired: run `palgu login` again".into(),
        Some("access_denied") => "sign-in was denied on the web".into(),
        Some("invalid_grant") => {
            "the code is unknown or was already used: run `palgu login` again".into()
        }
        _ => match status {
            Some(s) => format!("Palgu answered {s}"),
            None => "Palgu answered".into(),
        },
    }
}

fn signed_in(body: &Value) -> TokenStep {
    let key = body
        .get("access_token")
        .and_then(Value::as_str)
        .unwrap_or("");
    if key.is_empty() {
        return TokenStep::Stop("Palgu answered without a key".into());
    }
    let pick = |k: &str, f: &str| body.get(k).and_then(|v| v.get(f)).and_then(Value::as_str);
    TokenStep::Ok(Account {
        key: key.to_string(),
        email: pick("account", "email").unwrap_or("").to_string(),
        org: pick("org", "name").unwrap_or("").to_string(),
        plan: pick("org", "plan").unwrap_or("").to_string(),
    })
}

/// Pure decision over one `/auth/token` envelope: keep waiting, stop with a reason, or the minted key.
pub fn token_step(res: &Value, interval: u64) -> TokenStep {
    let empty = Value::Null;
    let body = res.get("body").unwrap_or(&empty);
    if res.get("ok").and_then(Value::as_bool).unwrap_or(false) {
        return signed_in(body);
    }
    match body.get("error").and_then(Value::as_str) {
        Some("authorization_pending") => TokenStep::Wait(interval),
        Some("slow_down") => TokenStep::Wait(interval + 5),
        err => TokenStep::Stop(stop_reason(err, res.get("status").and_then(Value::as_i64))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn err_env(status: i64, error: &str) -> Value {
        json!({"ok": false, "status": status, "body": {"error": error}})
    }

    #[test]
    fn minted_key_parses_account() {
        let res = json!({"ok": true, "status": 200, "body": {
            "access_token": "k-123",
            "account": {"email": "a@b.com"},
            "org": {"name": "Acme", "plan": "pro"}}});
        assert_eq!(
            token_step(&res, 5),
            TokenStep::Ok(Account {
                key: "k-123".into(),
                email: "a@b.com".into(),
                org: "Acme".into(),
                plan: "pro".into(),
            })
        );
    }

    #[test]
    fn ok_without_key_stops() {
        let res = json!({"ok": true, "status": 200, "body": {}});
        assert_eq!(
            token_step(&res, 5),
            TokenStep::Stop("Palgu answered without a key".into())
        );
    }

    #[test]
    fn pending_waits_same_interval() {
        assert_eq!(
            token_step(&err_env(400, "authorization_pending"), 5),
            TokenStep::Wait(5)
        );
    }

    #[test]
    fn slow_down_adds_five() {
        assert_eq!(
            token_step(&err_env(400, "slow_down"), 5),
            TokenStep::Wait(10)
        );
    }

    #[test]
    fn known_stop_reasons_match_python() {
        let cases = [
            ("expired_token", "the code expired: run `palgu login` again"),
            ("access_denied", "sign-in was denied on the web"),
            (
                "invalid_grant",
                "the code is unknown or was already used: run `palgu login` again",
            ),
        ];
        for (err, want) in cases {
            assert_eq!(
                token_step(&err_env(400, err), 5),
                TokenStep::Stop(want.into())
            );
        }
    }

    #[test]
    fn unknown_error_reports_status() {
        assert_eq!(
            token_step(&err_env(503, "boom"), 5),
            TokenStep::Stop("Palgu answered 503".into())
        );
    }
}
