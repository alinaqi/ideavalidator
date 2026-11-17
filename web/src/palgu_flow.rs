//! Request building and the network side of the Palgu device flow, over the injectable
//! [`PalguHttp`](crate::palgu::PalguHttp). Kept apart from the pure state machine so both stay small.

use rand::RngCore;
use serde_json::{json, Value};

use crate::palgu::{device_grant, DeviceStart, PalguHttp, CLIENT_ID, CLIENT_VERSION};

/// Who is signed in, without the key (used by the status surface). Mirrors `/me` -> account/org.
#[derive(Debug, Clone, PartialEq)]
pub struct Me {
    pub email: String,
    pub org: String,
    pub plan: String,
}

fn platform_tag(os: &str) -> &'static str {
    match os {
        "macos" => "darwin",
        "windows" => "win32",
        _ => "linux",
    }
}

fn random_install_id() -> String {
    let mut bytes = [0u8; 16];
    rand::rngs::OsRng.fill_bytes(&mut bytes);
    hex::encode(bytes)
}

/// Body for `POST /auth/device/code`, shaped exactly like `pipeline/palgu.py::device_body`.
pub fn device_body(name: &str, os: &str, install_id: &str) -> Value {
    json!({"client_id": CLIENT_ID, "device": {
        "name": name,
        "platform": platform_tag(os),
        "client_version": CLIENT_VERSION,
        "install_id": install_id,
    }})
}

/// Body for `POST /auth/token`, matching `pipeline/palgu.py::token_body`.
pub fn token_body(device_code: &str) -> Value {
    json!({"grant_type": device_grant(), "client_id": CLIENT_ID, "device_code": device_code})
}

fn parse_device_start(body: &Value) -> Result<DeviceStart, String> {
    let device_code = body
        .get("device_code")
        .and_then(Value::as_str)
        .unwrap_or("");
    if device_code.is_empty() {
        return Err("Palgu sign-in could not start".into());
    }
    let s = |k: &str| {
        body.get(k)
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string()
    };
    let n = |k: &str, d: u64| body.get(k).and_then(Value::as_u64).unwrap_or(d);
    Ok(DeviceStart {
        device_code: device_code.to_string(),
        user_code: s("user_code"),
        verification_uri: s("verification_uri"),
        interval: n("interval", 5),
        expires_in: n("expires_in", 600),
    })
}

/// Begin the device flow: ask Palgu for a device/user code pair.
pub async fn start_device(http: &dyn PalguHttp) -> Result<DeviceStart, String> {
    let body = device_body(
        "ideavalidator-web",
        std::env::consts::OS,
        &random_install_id(),
    );
    let res = http.post_json("/auth/device/code", body).await?;
    parse_device_start(res.get("body").unwrap_or(&Value::Null))
}

fn parse_me(body: &Value) -> Me {
    let pick = |k: &str, f: &str| body.get(k).and_then(|v| v.get(f)).and_then(Value::as_str);
    Me {
        email: pick("account", "email").unwrap_or("").to_string(),
        org: pick("org", "name").unwrap_or("").to_string(),
        plan: pick("org", "plan").unwrap_or("").to_string(),
    }
}

/// Look up the account behind a key via `GET /me`; `Err` if Palgu rejects it.
pub async fn fetch_me(http: &dyn PalguHttp, key: &str) -> Result<Me, String> {
    let res = http.get_json("/me", key).await?;
    if res.get("ok").and_then(Value::as_bool).unwrap_or(false) {
        Ok(parse_me(res.get("body").unwrap_or(&Value::Null)))
    } else {
        Err("Palgu rejected the key".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::palgu::PalguHttp;
    use async_trait::async_trait;
    use std::sync::Mutex;

    struct FakeHttp {
        posts: Mutex<Vec<Value>>,
        me: Value,
    }

    #[async_trait]
    impl PalguHttp for FakeHttp {
        async fn post_json(&self, _path: &str, _body: Value) -> Result<Value, String> {
            Ok(self.posts.lock().unwrap().remove(0))
        }
        async fn get_json(&self, _path: &str, _bearer: &str) -> Result<Value, String> {
            Ok(self.me.clone())
        }
    }

    fn fake(posts: Vec<Value>, me: Value) -> FakeHttp {
        FakeHttp {
            posts: Mutex::new(posts),
            me,
        }
    }

    #[test]
    fn device_body_shape_matches_python() {
        let b = device_body("box", "linux", "iid");
        assert_eq!(b["client_id"], "ideavalidator");
        assert_eq!(b["device"]["platform"], "linux");
        assert_eq!(b["device"]["install_id"], "iid");
    }

    #[test]
    fn token_body_carries_grant_and_code() {
        let b = token_body("dc-9");
        assert_eq!(b["device_code"], "dc-9");
        assert_eq!(
            b["grant_type"],
            "urn:ietf:params:oauth:grant-type:device_code"
        );
    }

    #[tokio::test]
    async fn start_device_parses_codes() {
        let http = fake(
            vec![json!({"ok": true, "body": {
                "device_code": "dc", "user_code": "WXYZ",
                "verification_uri": "https://palgu.ai/connect", "interval": 7, "expires_in": 300}})],
            Value::Null,
        );
        let start = start_device(&http).await.unwrap();
        assert_eq!(start.device_code, "dc");
        assert_eq!(start.user_code, "WXYZ");
        assert_eq!(start.interval, 7);
    }

    #[tokio::test]
    async fn start_device_without_code_errors() {
        let http = fake(vec![json!({"ok": true, "body": {}})], Value::Null);
        assert!(start_device(&http).await.is_err());
    }

    #[tokio::test]
    async fn fetch_me_reads_account() {
        let http = fake(
            vec![],
            json!({"ok": true, "body": {
            "account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "pro"}}}),
        );
        assert_eq!(
            fetch_me(&http, "k").await.unwrap(),
            Me {
                email: "a@b.com".into(),
                org: "Acme".into(),
                plan: "pro".into()
            }
        );
    }

    #[tokio::test]
    async fn fetch_me_rejects_bad_key() {
        let http = fake(vec![], json!({"ok": false, "body": {}}));
        assert!(fetch_me(&http, "k").await.is_err());
    }
}
