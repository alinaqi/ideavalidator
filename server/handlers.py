"""Testable tool logic for the hosted MCP server, kept out of the transport layer (app.py). Runs are keyed
to the caller's Palgu account and persisted in the run store, so get_status/get_report/list_runs work in a
new session. Dependencies (key store, run store, thread-spawner, client factory) are injected via `Deps`.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from pipeline.config import make_client
from . import tools
from .briefs import write_pitch_brief
from .keystore import settings_for
from .runjob import RunSpec, run_validation
from .store import RunRef


def _bg(fn, *args):  # pragma: no cover - thread spawn, exercised in production not unit tests
    threading.Thread(target=fn, args=args, daemon=True).start()


def _default_client(key: str, root):
    return make_client(settings_for(key, root))


@dataclass
class Deps:
    keys: object
    store: object
    root: Path
    spawn: object = None
    client_for: object = None


def start_validation(deps: Deps, sid: str, pitch: str) -> str:
    if not deps.keys.has(sid):
        return tools.NOT_SIGNED_IN
    ref, meta = deps.store.create(deps.keys.account(sid), "pending")
    slug, path = write_pitch_brief(deps.store.path(ref), pitch)
    deps.store.update(ref, {"slug": slug})
    meta["slug"] = slug
    client = (deps.client_for or _default_client)(deps.keys.get(sid), deps.root)
    spec = RunSpec(brief_path=path, out_root=deps.store.path(ref), client=client)
    (deps.spawn or _bg)(run_validation, deps.store, ref, spec)
    return tools.started_text(meta)


def status_for(deps: Deps, sid: str, run_id: str) -> dict:
    return tools.progress_payload(deps.store.get(RunRef(deps.keys.account(sid), run_id)))


def report_for(deps: Deps, sid: str, run_id: str) -> str:
    ref = RunRef(deps.keys.account(sid), run_id)
    return tools.report_text(deps.root, deps.store.path(ref), deps.store.get(ref))


def list_for(deps: Deps, sid: str) -> str:
    return tools.list_text(deps.store.list(deps.keys.account(sid)))


def cancel_for(deps: Deps, sid: str, run_id: str) -> str:
    meta = deps.store.update(RunRef(deps.keys.account(sid), run_id), {"cancel": True})
    return "Cancellation requested." if meta else "No such run_id."
