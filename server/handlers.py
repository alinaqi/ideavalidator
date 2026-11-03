"""Testable tool logic for the hosted MCP server, kept out of the transport layer (app.py) so it can be
unit-tested without an MCP context. Dependencies (key store, job registry, storage, thread-spawner,
client factory) are injected via `Deps`, so tests run the real pipeline with a fake client, synchronously.
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


def _bg(fn, *args):  # pragma: no cover - thread spawn, exercised in production not unit tests
    threading.Thread(target=fn, args=args, daemon=True).start()


def _default_client(key: str, root):
    return make_client(settings_for(key, root))


@dataclass
class Deps:
    keys: object
    jobs: object
    store: Path
    root: Path
    spawn: object = None
    client_for: object = None


def start_validation(deps: Deps, sid: str, pitch: str) -> str:
    if not deps.keys.has(sid):
        return tools.NOT_SIGNED_IN
    slug, path = write_pitch_brief(Path(deps.store) / sid / "ideas", pitch)
    job = deps.jobs.create(sid, slug)
    client = (deps.client_for or _default_client)(deps.keys.get(sid), deps.root)
    spec = RunSpec(brief_path=path, out_root=Path(deps.store) / sid / "runs", client=client)
    (deps.spawn or _bg)(run_validation, job.id, deps.jobs, spec)
    return tools.started_text(job)


def report_for(deps: Deps, sid: str, run_id: str) -> str:
    job = deps.jobs.get(run_id)
    run_dir = Path(deps.store) / sid / "runs" / (job.slug if job else "_")
    return tools.report_text(deps.root, run_dir, job)
