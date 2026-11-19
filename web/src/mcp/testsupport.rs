//! Shared in-crate test scaffolding for the MCP unit tests: a scripted [`PalguHttp`] and an [`AppState`]
//! wired to an in-memory DB, a no-op worker spawner and a real cipher. No network, no Postgres, no Python.

use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use serde_json::{json, Value};
use tokio::sync::Semaphore;

use crate::config::Config;
use crate::crypto::Cipher;
use crate::db::InMemoryDb;
use crate::mcp::sessions::new_mcp_sessions;
use crate::palgu::PalguHttp;
use crate::runs::RunRegistry;
use crate::sse::SseHub;
use crate::state::{new_pending_map, AppState};
use crate::worker_proc::NoopSpawner;

pub const KEY_HEX: &str = "3333333333333333333333333333333333333333333333333333333333333333";

/// A Palgu transport driven by canned responses: one device-code body, a queue of `/auth/token`
/// envelopes, and a fixed `/me` envelope.
pub struct ScriptedPalgu {
    pub device: Value,
    pub tokens: Mutex<Vec<Value>>,
    pub me: Value,
}

#[async_trait]
impl PalguHttp for ScriptedPalgu {
    async fn post_json(&self, path: &str, _body: Value) -> Result<Value, String> {
        if path == "/auth/device/code" {
            Ok(self.device.clone())
        } else {
            Ok(self.tokens.lock().unwrap().remove(0))
        }
    }
    async fn get_json(&self, _path: &str, _bearer: &str) -> Result<Value, String> {
        Ok(self.me.clone())
    }
}

/// A device-code start envelope with an immediate (interval 0) poll so tests never sleep.
pub fn device_ok() -> Value {
    json!({"ok": true, "body": {"device_code": "dc", "user_code": "WXYZ",
        "verification_uri": "https://www.palgu.ai/connect", "interval": 0, "expires_in": 600}})
}

/// A successful `/auth/token` envelope minting a key for `a@b.com` on the `pro` plan.
pub fn token_success() -> Value {
    json!({"ok": true, "status": 200, "body": {"access_token": "k-1",
        "account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "pro"}}})
}

/// A `/me` envelope for the same account.
pub fn me_ok() -> Value {
    json!({"ok": true, "body": {"account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "pro"}}})
}

fn store_dir() -> String {
    std::env::temp_dir()
        .join(format!("iv-mcp-{}", std::process::id()))
        .to_string_lossy()
        .into_owned()
}

/// Build an [`AppState`] around a scripted Palgu transport.
pub fn state_with(palgu: ScriptedPalgu) -> AppState {
    let dir = store_dir();
    let cfg = Config::from(move |k| match k {
        "TOKEN_ENC_KEY" => Some(KEY_HEX.to_string()),
        "IV_STORE" => Some(dir.clone()),
        _ => None,
    });
    AppState {
        db: Arc::new(InMemoryDb::new()),
        palgu: Arc::new(palgu),
        cipher: Arc::new(Cipher::from_env_key(KEY_HEX).unwrap()),
        config: cfg,
        pending: new_pending_map(),
        spawner: Arc::new(NoopSpawner),
        hub: Arc::new(SseHub::new()),
        sem: Arc::new(Semaphore::new(2)),
        runs: RunRegistry::new(),
        mcp: new_mcp_sessions(),
        checker: std::sync::Arc::new(crate::reqcheck_proc::UnavailableChecker),
    }
}

/// A scripted Palgu that signs in on the first `/auth/token` poll.
pub fn signing_in() -> ScriptedPalgu {
    ScriptedPalgu {
        device: device_ok(),
        tokens: Mutex::new(vec![token_success()]),
        me: me_ok(),
    }
}
