"""Pure response builders for the hosted MCP tools, kept out of the transport layer so they are
unit-testable. Each returns the plain text a tool hands back to the calling assistant.
"""
from __future__ import annotations

from pathlib import Path

NOT_SIGNED_IN = ("Not signed in to Palgu. Run the `palgu_login` tool first (approve the code at "
                 "palgu.ai), then retry — the validation runs on your own Palgu key.")


def started_text(job) -> str:
    return (f"Validation started for '{job.slug}'. run_id: {job.id}\n"
            f"Poll with get_status(run_id='{job.id}'); fetch the memo with get_report when it's done "
            "(a full run takes ~20-40 min).")


def progress_text(job) -> str:
    if job is None:
        return "No such run_id."
    head = f"Run {job.id} ({job.slug}): {job.state}"
    if job.state == "error":
        return f"{head} — {job.error}"
    lines = [f"  {s['stage']}: {s['verdict']} ({s['score']})" for s in job.stages]
    return head + ("\n" + "\n".join(lines) if lines else "")


def report_text(root, run_dir, job) -> str:
    if job is None:
        return "No such run_id."
    if job.state != "done":
        return progress_text(job) + "\n(report available once state is 'done')"
    memo = Path(run_dir) / "decision.md"
    if memo.exists():
        return memo.read_text()
    from pipeline.report_export import ReportJob, cli_report
    return cli_report(ReportJob(run_dir=Path(run_dir), fmt="md", dest=None, root=Path(root)))
