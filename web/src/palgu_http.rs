//! Real [`PalguHttp`](crate::palgu::PalguHttp) over reqwest (rustls, no OpenSSL). Wired only in
//! `main()`; the flow and state machine are tested with scripted fakes, so this file has no unit tests.

use async_trait::async_trait;
use reqwest::{Client, Response};
use serde_json::{json, Value};

use crate::palgu::PalguHttp;

pub struct ReqwestHttp {
    base: String,
    client: Client,
}

impl ReqwestHttp {
    pub fn new(base: String) -> Self {
        ReqwestHttp {
            base,
            client: Client::new(),
        }
    }

    fn url(&self, path: &str) -> String {
        format!("{}{}", self.base, path)
    }
}

async fn envelope(resp: Response) -> Value {
    let status = resp.status().as_u16();
    let body = resp.json::<Value>().await.unwrap_or(Value::Null);
    json!({"ok": status < 400, "status": status, "body": body})
}

#[async_trait]
impl PalguHttp for ReqwestHttp {
    async fn post_json(&self, path: &str, body: Value) -> Result<Value, String> {
        let resp = self
            .client
            .post(self.url(path))
            .json(&body)
            .send()
            .await
            .map_err(|e| e.to_string())?;
        Ok(envelope(resp).await)
    }

    async fn get_json(&self, path: &str, bearer: &str) -> Result<Value, String> {
        let resp = self
            .client
            .get(self.url(path))
            .bearer_auth(bearer)
            .send()
            .await
            .map_err(|e| e.to_string())?;
        Ok(envelope(resp).await)
    }
}
