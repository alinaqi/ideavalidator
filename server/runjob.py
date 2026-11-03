"""Runs one validation job against the shared pipeline engine, persisting progress to the run store so a
new session can read it. Checks the run's cancel flag between stages (cooperative cancel). Synchronous and
client-injected (unit-testable); the MCP app launches it on a background thread.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pipeline.prompts import load_brief
from pipeline.runner import RunContext, run_stage
from pipeline.stages import resolve


@dataclass
class RunSpec:
    brief_path: Path
    out_root: Path
    client: object
    stages: str = "all"


def run_validation(store, ref, spec: RunSpec) -> None:
    store.update(ref, {"state": "running"})
    try:
        brief = load_brief(Path(spec.brief_path))
        ctx = RunContext(brief=brief, out_dir=Path(spec.out_root) / brief.slug, client=spec.client)
        for stage in resolve(spec.stages):
            if (store.get(ref) or {}).get("cancel"):
                store.update(ref, {"state": "cancelled"})
                return
            gate = run_stage(stage, ctx)["gate"]
            store.record_stage(ref, {"stage": stage.id, "verdict": gate["verdict"], "score": gate["score"]})
        store.update(ref, {"state": "done"})
    except Exception as exc:  # best-effort: surface any failure as the run's error, never crash the worker
        store.update(ref, {"state": "error", "error": str(exc)})
