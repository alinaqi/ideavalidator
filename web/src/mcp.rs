//! Hosted MCP endpoint at `/mcp` (streamable-HTTP JSON-RPC), at parity with the Python `server/` tools
//! (`palgu_login`, `palgu_status`, `validate_idea`, `get_status`, `list_runs`, `cancel_run`,
//! `get_report`). The transport ([`http`]) is kept thin; the tool logic is pure ([`tools`]) or a small
//! async dispatch over the shared [`crate::state::AppState`] ([`dispatch`]), so every tool's response is
//! unit-tested against the Python-parity strings with an in-memory DB and a fake spawner.

pub mod dispatch;
pub mod http;
pub mod login;
pub mod rpc;
pub mod sessions;
pub mod tools;

#[cfg(test)]
pub(crate) mod testsupport;
