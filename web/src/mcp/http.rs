//! Streamable-HTTP MCP transport at `/mcp`: a thin JSON-RPC-over-HTTP handler covering `initialize`,
//! `tools/list` and `tools/call` (with notifications acknowledged). Each POST carries one JSON-RPC
//! message; the response is `application/json`. The MCP session id travels in the `Mcp-Session-Id`
//! header (minted on `initialize`), binding a browser-less caller to its Palgu account via
//! [`crate::mcp::sessions`]. All tool logic lives in [`crate::mcp::dispatch`]; this file is wiring only.

use axum::extract::State;
use axum::http::header::HeaderName;
use axum::http::{HeaderMap, HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde_json::{json, Value};

use crate::mcp::{dispatch, rpc, tools};
use crate::session::new_token;
use crate::state::AppState;

const SESSION_HEADER: &str = "mcp-session-id";

fn provided_session(headers: &HeaderMap) -> Option<String> {
    headers
        .get(SESSION_HEADER)
        .and_then(|v| v.to_str().ok())
        .map(str::to_string)
}

fn session_id(headers: &HeaderMap) -> String {
    provided_session(headers).unwrap_or_else(|| "local".to_string())
}

fn json_reply(body: Value) -> Response {
    Json(body).into_response()
}

/// `POST /mcp`: one JSON-RPC request or notification.
pub async fn mcp_post(
    State(st): State<AppState>,
    headers: HeaderMap,
    body: Option<Json<Value>>,
) -> Response {
    let Some(Json(req)) = body else {
        return json_reply(rpc::error(Value::Null, -32700, "Parse error"));
    };
    if rpc::is_notification(&req) {
        return StatusCode::ACCEPTED.into_response();
    }
    dispatch_method(&st, &headers, &req).await
}

async fn dispatch_method(st: &AppState, headers: &HeaderMap, req: &Value) -> Response {
    let id = rpc::req_id(req);
    match rpc::req_method(req) {
        "initialize" => initialize(headers, req, id),
        "tools/list" => json_reply(rpc::ok(id, json!({ "tools": tools::tool_specs() }))),
        "tools/call" => tools_call(st, headers, req, id).await,
        _ => json_reply(rpc::error(id, rpc::METHOD_NOT_FOUND, "Method not found")),
    }
}

fn initialize(headers: &HeaderMap, req: &Value, id: Value) -> Response {
    let protocol = req["params"]["protocolVersion"]
        .as_str()
        .unwrap_or(rpc::PROTOCOL_VERSION);
    let sid = provided_session(headers).unwrap_or_else(new_token);
    let mut resp = json_reply(rpc::ok(id, rpc::initialize_result(protocol)));
    if let Ok(value) = HeaderValue::from_str(&sid) {
        resp.headers_mut()
            .insert(HeaderName::from_static(SESSION_HEADER), value);
    }
    resp
}

async fn tools_call(st: &AppState, headers: &HeaderMap, req: &Value, id: Value) -> Response {
    let params = &req["params"];
    let name = params["name"].as_str().unwrap_or("");
    let empty = json!({});
    let args = params.get("arguments").unwrap_or(&empty);
    let result = dispatch::call_tool(st, &session_id(headers), name, args).await;
    json_reply(rpc::ok(id, result))
}

/// `GET /mcp`: this minimal transport does not open a server-initiated SSE stream.
pub async fn mcp_get() -> Response {
    StatusCode::METHOD_NOT_ALLOWED.into_response()
}
