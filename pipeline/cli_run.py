"""The `run` command's stage loop, split from cli.py to keep that file within the functions-per-file
limit. Streams each gate verdict and writes a progress file per stage for the live status-line mod.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .progress import ProgressStep, write_progress
from .report_export import ReportJob, cli_report
from .runner import MissingDependency, run_stage
from .stages import resolve


def report_cmd(args, root) -> int:
    job = ReportJob(run_dir=Path(args.out) / args.idea, fmt=args.format,
                    dest=Path(args.dest) if args.dest else None, root=root)
    print(cli_report(job))
    return 0


def run_stages(args, ctx) -> int:
    stages = resolve(args.stages)
    total = len(stages)
    for i, stage in enumerate(stages, 1):
        print(f"→ {stage.id}: {stage.name} …", flush=True)
        write_progress(ctx.out_dir, ProgressStep(i, total, stage.id, "running"))
        try:
            gate = run_stage(stage, ctx)["gate"]
        except MissingDependency as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        write_progress(ctx.out_dir, ProgressStep(i, total, stage.id, "done", gate["verdict"], gate["score"]))
        print(f"  {gate['verdict']} (score {gate['score']}) → {ctx.out_dir / stage.id}.md")
        if args.stop_on_kill and gate["verdict"] == "KILL":
            print(f"stopped: {stage.id} gate is KILL ({'; '.join(gate['reasons'])})")
            return 3
    write_progress(ctx.out_dir, ProgressStep(total, total, "complete", "complete"))
    return 0
