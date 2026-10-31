"""Council inputs (dossier) and outputs (markdown)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .stages import STAGES

MAX_EVIDENCE = 40
VOTES = ("GO", "PIVOT", "KILL")


def label(text: str, name: str) -> str:
    """Value of a `Name: value` line anywhere in the text (case-insensitive)."""
    match = re.search(rf"^\s*{name}:\s*(.+?)\s*$", text or "", re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_vote(text: str) -> dict:
    vote = label(text, "Vote").upper().split()
    return {"framework": label(text, "Framework"),
            "vote": next((v for v in VOTES if vote and vote[0].startswith(v)), "UNKNOWN"),
            "enrichment": label(text, "Enrichment"), "verify": label(text, "Verify")}


def _evidence_lines(data: dict) -> list:
    return [f"- [{e.get('behavior_vs_stated')}/{e.get('directness')}/{e.get('recency')}] "
            f"{e.get('claim')} ({e.get('source_url', '')})"
            for e in data.get("evidence") or [] if e.get("claim")]


def board_dossier(brief, out_dir: Path) -> str:
    """Brief + every finished stage summary + labelled evidence + unknowns."""
    parts = [f"# Idea brief: {brief.title}\n\n{brief.body.strip()}"]
    evidence, unknowns = [], []
    for stage in STAGES:
        path = out_dir / f"{stage.id}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        gate = (data.get("gate") or {}).get("verdict", "")
        parts.append(f"## Desk research — {stage.id} (gate {gate})\n{data.get('summary', '')}")
        evidence += _evidence_lines(data)
        unknowns += [f"- {u}" for u in data.get("unknowns") or []]
    parts.append("## Evidence ledger (label = behaviour-vs-stated / directness / recency)\n"
                 + ("\n".join(evidence[:MAX_EVIDENCE]) or "(no desk research yet)"))
    parts.append("## Open unknowns\n" + ("\n".join(unknowns[:25]) or "(none recorded)"))
    return "\n\n".join(parts)


def _member_block(m: dict) -> str:
    head = f"### {m['role']} — {m['model']}"
    if m.get("error"):
        return f"{head}\n\n_failed: {m['error']}_\n"
    return (f"{head} · framework: {m.get('framework')} · vote: **{m.get('vote')}**\n\n{m.get('text', '')}\n\n"
            f"Enrichment: {m.get('enrichment', '')}\n\nVerify: {m.get('verify', '')}\n")


def render_council(data: dict) -> str:
    syn = data.get("synthesis") or {}
    rec = syn.get("recommendation") or {}
    votes = ", ".join(f"{v.get('role')}={v.get('vote')}" for v in syn.get("votes") or [])
    parts = [f"# COUNCIL — {data.get('idea', '')}\n\nmodels: {', '.join(data.get('models', []))} · "
             f"rounds: {data.get('rounds')} · generated: {data.get('generated_at', '')}\n\n"
             f"**Recommendation: {rec.get('verdict', 'UNKNOWN')}** — {rec.get('rationale', '')}\n\n"
             f"Votes: {votes}\n\n## Chair's synthesis\n\n{data.get('synthesis_markdown', '')}\n",
             "## Opening statements\n"]
    parts += [_member_block(m) for m in data.get("members", [])]
    if data.get("debate"):
        parts.append("## Debate\n" + "\n\n".join(
            f"**{d['role']}** ({d['model']}): {d['text']}" for d in data["debate"]))
    if data.get("red_team"):
        rt = data["red_team"]
        parts.append(f"## Red Team — {rt['model']}\n\n**{rt.get('position')}**\n\n{rt.get('text', '')}")
    return "\n".join(parts)


def write_council(out_dir: Path, data: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "council.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    (out_dir / "council.md").write_text(render_council(data))
