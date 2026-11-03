"""The hosted ideavalidator remote MCP server (streamable HTTP). Thin transport layer only: tools bind to
the tested pure modules (handlers, tools, palgu_session). Bring-your-own-Palgu — a caller runs
`palgu_login`, then `validate_idea` runs the pipeline on their own key. State is per MCP session
(`ctx.session_id`), in-memory for v0.1. Add as a connector in claude.ai / ChatGPT / Grok (URL: /mcp).
"""
from __future__ import annotations

import os
from pathlib import Path

from mcp.server.mcpserver import Context, MCPServer

from . import handlers, tools
from .handlers import Deps
from .jobs import JobRegistry
from .keystore import KeyStore
from .palgu_session import DeviceLogin

ROOT = Path(__file__).resolve().parents[1]
STORE = Path(os.environ.get("IV_STORE") or (ROOT / "server_runs"))

_keys = KeyStore()
_jobs = JobRegistry()
_login = DeviceLogin(_keys)
_deps = Deps(keys=_keys, jobs=_jobs, store=STORE, root=ROOT)

mcp = MCPServer("ideavalidator", instructions=(
    "Validate a business idea end to end (problem, market, ICP, SWOT, pricing, day-one economics, "
    "risks, GO/PIVOT/KILL). Run `palgu_login` once to sign in with your own Palgu key, then "
    "`validate_idea`, poll `get_status`, and read `get_report`."))


def _sid(ctx) -> str:
    return getattr(ctx, "session_id", None) or "local"


@mcp.tool()
def palgu_login(ctx: Context) -> str:
    """Sign in to your Palgu account (approve a code at palgu.ai). Required before validating."""
    return _login.login_async(_sid(ctx))["text"]


@mcp.tool()
def palgu_status(ctx: Context) -> str:
    """Show whether this session is signed in to Palgu, and on which plan."""
    return _login.status(_sid(ctx))


@mcp.tool()
def validate_idea(pitch: str, ctx: Context) -> str:
    """Start validating a business idea from a one-sentence pitch. Returns a run_id to poll."""
    return handlers.start_validation(_deps, _sid(ctx), pitch)


@mcp.tool()
def get_status(run_id: str, ctx: Context) -> str:
    """Check progress and per-stage verdicts of a validation run."""
    return tools.progress_text(_jobs.get(run_id))


@mcp.tool()
def get_report(run_id: str, ctx: Context) -> str:
    """Get the GO/PIVOT/KILL decision memo for a completed run."""
    return handlers.report_for(_deps, _sid(ctx), run_id)


app = mcp.streamable_http_app()
