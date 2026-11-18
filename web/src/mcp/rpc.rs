//! Pure JSON-RPC 2.0 envelope helpers for the MCP transport: build `result`/`error` replies, the
//! `initialize` handshake and a `tools/call` text result, and read a request's id/method. No IO, so the
//! whole envelope layer is unit-tested; [`crate::mcp::http`] only wires these to axum.

use serde_json::{json, Value};

/// MCP protocol version this server speaks (echoed back on `initialize` when a client sends none).
pub const PROTOCOL_VERSION: &str = "2025-06-18";

/// Standard JSON-RPC error code for an unknown method.
pub const METHOD_NOT_FOUND: i64 = -32601;
/// Standard JSON-RPC error code for invalid parameters.
pub const INVALID_PARAMS: i64 = -32602;

/// A successful JSON-RPC response.
pub fn ok(id: Value, result: Value) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "result": result})
}

/// A JSON-RPC error response.
pub fn error(id: Value, code: i64, message: &str) -> Value {
    json!({"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}})
}

/// The `initialize` result: protocol version, the tools capability, and server identity.
pub fn initialize_result(protocol: &str) -> Value {
    json!({
        "protocolVersion": protocol,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "ideavalidator", "version": "0.1.0"},
    })
}

/// Wrap tool output as a `tools/call` result (one text block).
pub fn tool_text(text: &str) -> Value {
    json!({"content": [{"type": "text", "text": text}], "isError": false})
}

/// Wrap a structured value as a `tools/call` result: the JSON as text plus `structuredContent`.
pub fn tool_json(value: Value) -> Value {
    json!({
        "content": [{"type": "text", "text": value.to_string()}],
        "structuredContent": value,
        "isError": false,
    })
}

/// A `tools/call` result flagged as an error (e.g. an unknown tool name).
pub fn tool_error(message: &str) -> Value {
    json!({"content": [{"type": "text", "text": message}], "isError": true})
}

/// The request id, or JSON `null` when absent (notifications).
pub fn req_id(req: &Value) -> Value {
    req.get("id").cloned().unwrap_or(Value::Null)
}

/// The request method name, or `""`.
pub fn req_method(req: &Value) -> &str {
    req.get("method").and_then(Value::as_str).unwrap_or("")
}

/// A notification is a request without an `id` (no response is sent).
pub fn is_notification(req: &Value) -> bool {
    req.get("id").is_none()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ok_and_error_carry_the_id() {
        assert_eq!(ok(json!(1), json!({"x": 2}))["id"], 1);
        let e = error(json!("a"), METHOD_NOT_FOUND, "nope");
        assert_eq!(e["error"]["code"], -32601);
        assert_eq!(e["error"]["message"], "nope");
    }

    #[test]
    fn initialize_advertises_tools_capability() {
        let r = initialize_result(PROTOCOL_VERSION);
        assert_eq!(r["protocolVersion"], "2025-06-18");
        assert!(r["capabilities"]["tools"].is_object());
        assert_eq!(r["serverInfo"]["name"], "ideavalidator");
    }

    #[test]
    fn tool_text_is_a_single_content_block() {
        let r = tool_text("hello");
        assert_eq!(r["content"][0]["type"], "text");
        assert_eq!(r["content"][0]["text"], "hello");
        assert_eq!(r["isError"], false);
    }

    #[test]
    fn method_and_notification_are_read() {
        let notif = json!({"jsonrpc": "2.0", "method": "notifications/initialized"});
        assert!(is_notification(&notif));
        assert_eq!(req_method(&notif), "notifications/initialized");
        assert_eq!(req_id(&notif), Value::Null);
        let call = json!({"jsonrpc": "2.0", "id": 7, "method": "tools/list"});
        assert!(!is_notification(&call));
        assert_eq!(req_id(&call), 7);
    }
}
