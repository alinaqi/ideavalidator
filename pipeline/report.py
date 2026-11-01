"""Markdown rendering for stage outputs and the final decision memo."""
from __future__ import annotations

import json

from .gates import Gate, rollup
from .stages import STAGES

ENVELOPE = {"stage", "idea", "model", "generated_at", "summary", "scores", "kill_flags",
            "evidence", "unknowns", "gate", "sources", "triangulation",
            "search_queries", "pdlc_state"}


def _fmt(value) -> str:
    if isinstance(value, dict):
        return "; ".join(f"**{k}**: {_fmt(v)}" for k, v in value.items())
    if isinstance(value, list):
        return "\n".join(f"- {_fmt(v)}" for v in value) if value else "(none)"
    return str(value)


def _section(title: str, value) -> str:
    body = _fmt(value)
    if isinstance(value, dict):
        body = "\n".join(f"- **{k}**: {_fmt(v)}" for k, v in value.items())
    return f"## {title.replace('_', ' ').capitalize()}\n\n{body}\n"


def _scores_table(data: dict) -> str:
    scores = data.get("scores") or {}
    rows = "\n".join(f"| {k} | {v} |" for k, v in scores.items())
    flags = ", ".join(data.get("kill_flags") or []) or "none"
    return f"## Scores (0-5)\n\n| Criterion | Score |\n|---|---|\n{rows}\n\nKill flags: {flags}\n"


def _evidence_table(data: dict) -> str:
    head = ("## Evidence ledger\n\n| Claim | Source | Type | Direct | Behav/Stated | Recency |\n"
            "|---|---|---|---|---|---|\n")
    rows = [f"| {e['claim']} | {e.get('source_url', '')} | {e.get('source_type', '')} | "
            f"{e.get('directness')} | {e.get('behavior_vs_stated')} | {e.get('recency')} |"
            for e in data.get("evidence") or []]
    tri = data.get("triangulation") or {}
    return head + "\n".join(rows) + f"\n\nTriangulation: {json.dumps(tri)}\n"


def _header(data: dict) -> str:
    gate = data.get("gate") or {}
    reasons = "; ".join(gate.get("reasons") or [])
    return (f"# {str(data.get('stage', '?')).upper()} — {data.get('idea', '')}\n\n"
            f"PDLC state: {data.get('pdlc_state', '')} · model: {data.get('model', '')} · "
            f"generated: {data.get('generated_at', '')}\n\n"
            f"**Gate: {gate.get('verdict', 'UNKNOWN')}** (score {gate.get('score', 0)}) — {reasons}\n\n"
            f"## Summary\n\n{data.get('summary', '')}\n")


def render_stage(data: dict) -> str:
    parts = [_header(data), _scores_table(data)]
    parts += [_section(k, v) for k, v in data.items() if k not in ENVELOPE]
    parts.append(_evidence_table(data))
    parts.append(_section("unknowns", data.get("unknowns") or []))
    sources = [f"{s.get('title') or s['url']} — {s['url']}" for s in data.get("sources") or []]
    parts.append(_section("sources", sources))
    return "\n".join(parts)


def _memo_rows(out_dir) -> tuple:
    rows, gates = [], []
    for stage in STAGES:
        path = out_dir / f"{stage.id}.json"
        if not path.exists():
            rows.append(f"| {stage.id} | not yet run | — | |")
            continue
        data = json.loads(path.read_text())
        gate = Gate(**{k: data.get("gate", {}).get(k) for k in ("stage", "verdict", "score", "reasons")})
        gates.append(gate)
        rows.append(f"| {stage.id} | {gate.verdict} | {gate.score} | {data.get('summary', '')[:160]} |")
    return rows, gates


def _signals_block(out_dir) -> str:
    path = out_dir / "signals.json"
    if not path.exists():
        return ""
    d = json.loads(path.read_text())
    vol = "; ".join(f"{s.get('label')}: {int(s.get('value') or 0)}/mo" for s in d.get("search") or [])
    soc = "; ".join(f"{s.get('label')} ({s.get('source')})" for s in (d.get("social") or [])[:5])
    return (f"\n\n## Demand signals (additive bonus +{d.get('bonus', 0):g})\n\n"
            f"Query **{d.get('query', '')}** · search volume: {vol or 'none'} · "
            f"social: {soc or 'none'}. _Absence is not evidence against the idea._")


def _selfcheck_block(out_dir) -> str:
    path = out_dir / "selfcheck.md"
    return "\n\n---\n\n" + path.read_text() if path.exists() else ""


def build_memo(out_dir) -> str:
    rows, gates = _memo_rows(out_dir)
    overall = rollup(gates)
    decision = out_dir / "decision.md"
    tail = decision.read_text() if decision.exists() else "_Decision stage not yet run._"
    return (f"# Decision memo — {out_dir.name}\n\n**Overall verdict: {overall.verdict}** "
            f"(mean gate score {overall.score})\n\n| Stage | Verdict | Score | Summary |\n"
            f"|---|---|---|---|\n" + "\n".join(rows) + _signals_block(out_dir)
            + _selfcheck_block(out_dir) + "\n\n---\n\n" + tail)
