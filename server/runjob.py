"""Runs one validation job against the shared pipeline engine and streams per-stage verdicts into the
job registry. Synchronous and client-injected (so it is unit-testable without network); the MCP app
launches it on a background thread so the `validate_idea` tool can return a run id immediately.
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


def run_validation(job_id: str, registry, spec: RunSpec) -> None:
    registry.start(job_id)
    try:
        brief = load_brief(Path(spec.brief_path))
        ctx = RunContext(brief=brief, out_dir=Path(spec.out_root) / brief.slug, client=spec.client)
        for stage in resolve(spec.stages):
            gate = run_stage(stage, ctx)["gate"]
            registry.record_stage(job_id, stage.id, gate["verdict"], gate["score"])
        registry.finish(job_id)
    except Exception as exc:  # best-effort: surface any failure as job error, never crash the worker
        registry.fail(job_id, str(exc))
