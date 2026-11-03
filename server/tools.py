"""Pure response builders for the hosted MCP tools, kept out of the transport layer so they are
unit-testable. Each takes a run's stored meta dict (or a list of them) and returns what a tool hands back.
"""
from __future__ import annotations

from pathlib import Path

from pipeline.stages import STAGES

TOTAL = len(STAGES)
NOT_SIGNED_IN = ("Not signed in to Palgu. Run the `palgu_login` tool first (approve the code at "
                 "palgu.ai), then retry — the validation runs on your own Palgu key.")


def next_poll_seconds(state: str) -> int:
    return {"pending": 20, "running": 120}.get(state, 0)


def started_text(meta: dict) -> str:
    return (f"Validation started for '{meta['slug']}'. run_id: {meta['run_id']}\n"
            f"Poll get_status(run_id='{meta['run_id']}') about every 2 minutes; read get_report when "
            "state is 'done' (a full run takes ~20-40 min).")


def progress_payload(meta) -> dict:
    if meta is None:
        return {"error": "No such run_id."}
    return {"run_id": meta["run_id"], "slug": meta["slug"], "state": meta["state"],
            "completed": len(meta["stages"]), "total": TOTAL, "stages": meta["stages"],
            "next_poll_seconds": next_poll_seconds(meta["state"]), "error": meta.get("error", "")}


def list_text(metas: list) -> str:
    if not metas:
        return "No runs yet."
    return "\n".join(f"{m['run_id']}  {m['state']:9} {len(m['stages'])}/{TOTAL}  {m['slug']}" for m in metas)


def report_text(root, run_dir, meta) -> str:
    if meta is None:
        return "No such run_id."
    if meta["state"] != "done":
        return (f"Run {meta['run_id']} is {meta['state']} ({len(meta['stages'])}/{TOTAL}). "
                "The report is available once state is 'done'.")
    stage_dir = Path(run_dir) / meta["slug"]
    memo = stage_dir / "decision.md"
    if memo.exists():
        return memo.read_text()
    from pipeline.report_export import ReportJob, cli_report
    return cli_report(ReportJob(run_dir=stage_dir, fmt="md", dest=None, root=Path(root)))
