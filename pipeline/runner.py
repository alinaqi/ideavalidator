"""Run one validation stage: prompt → grounded research → JSON → gate → files."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .evidence import normalize, triangulate
from .gates import evaluate
from .prompts import Brief, load_schema, render
from .report import render_stage


class MissingDependency(RuntimeError):
    """A stage was requested before the stages it builds on."""


_BOOSTED = ("market", "problem", "decision")


@dataclass
class RunContext:
    brief: Brief
    out_dir: Path
    client: object
    deep: bool = False
    signal_bonus: float = 0.0
    signals_summary: str = ""


def load_output(out_dir: Path, stage_id: str):
    path = out_dir / f"{stage_id}.json"
    return json.loads(path.read_text()) if path.exists() else None


def prior_summaries(out_dir: Path, stage_ids) -> dict:
    found = {}
    for sid in stage_ids:
        data = load_output(out_dir, sid)
        if data:
            found[sid] = str(data.get("summary") or "").strip()
    return found


def _check_deps(stage, out_dir: Path) -> None:
    missing = [d for d in stage.depends_on if load_output(out_dir, d) is None]
    if missing:
        raise MissingDependency(
            f"stage '{stage.id}' depends on {missing}; run those stages first")


def _investigate(ctx: RunContext, prompt: str):
    return ctx.client.deep_research(prompt) if ctx.deep else ctx.client.research(prompt)


def _structure(ctx: RunContext, stage, research) -> dict:
    cites = "\n".join(f"- {s.get('title') or s['url']}: {s['url']}" for s in research.sources)
    notes = f"{research.text}\n\nGROUNDED SOURCES:\n{cites or '(none)'}"
    return ctx.client.structure(notes, load_schema(stage))


def finalize(stage, data: dict, research) -> dict:
    """Attach envelope fields, normalised evidence, triangulation and the gate."""
    raw = [e for e in data.get("evidence") or [] if isinstance(e, dict) and e.get("claim")]
    evidence = [normalize(e) for e in raw]
    data.update({
        "stage": stage.id,
        "pdlc_state": stage.pdlc_state,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": research.sources,
        "search_queries": research.queries,
        "evidence": evidence,
        "triangulation": triangulate(evidence),
    })
    data["gate"] = asdict(evaluate(stage.id, data))
    return data


def write_outputs(out_dir: Path, stage_id: str, data: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{stage_id}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    (out_dir / f"{stage_id}.md").write_text(render_stage(data))


def _prior_for(stage, ctx: RunContext) -> dict:
    prior = prior_summaries(ctx.out_dir, stage.depends_on + stage.optional)
    if ctx.signals_summary and stage.id in _BOOSTED:
        prior["demand_signals"] = ctx.signals_summary
    return prior


def run_stage(stage, ctx: RunContext) -> dict:
    _check_deps(stage, ctx.out_dir)
    prompt = render(stage, ctx.brief, _prior_for(stage, ctx))
    research = _investigate(ctx, prompt)
    data = _structure(ctx, stage, research)
    from .modes import resolve as mode_resolve
    from .objectives import resolve
    data["objective"] = resolve(ctx.brief).key
    data["validation_mode"] = mode_resolve(ctx.brief).key
    if stage.id in _BOOSTED:
        data["signal_bonus"] = ctx.signal_bonus
    data = finalize(stage, data, research)
    data["idea"] = ctx.brief.slug
    data["model"] = research.model or getattr(ctx.client, "model", "")
    write_outputs(ctx.out_dir, stage.id, data)
    return data
