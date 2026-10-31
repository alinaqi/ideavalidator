"""Command line: `python -m pipeline.cli run|report|stages`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import MissingKeyError, Settings
from .gemini import GeminiClient
from .prompts import PROMPT_DIR, SCHEMA_DIR, load_brief
from .report import build_memo
from .runner import MissingDependency, RunContext, run_stage
from .stages import STAGES, resolve

ROOT = Path(__file__).resolve().parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run validation stages for an idea brief")
    run.add_argument("--idea", required=True, help="path to ideas/<slug>.md")
    run.add_argument("--stages", default="all", help="'all' or comma list of stage ids")
    run.add_argument("--out", default=str(ROOT / "runs"), help="runs directory")
    run.add_argument("--deep", action="store_true", help="use Gemini Deep Research")
    run.add_argument("--stop-on-kill", action="store_true",
                     help="halt after the first stage whose gate is KILL")
    rep = sub.add_parser("report", help="print the decision memo for an idea slug")
    rep.add_argument("--idea", required=True, help="idea slug (runs/<slug>)")
    rep.add_argument("--out", default=str(ROOT / "runs"))
    sub.add_parser("stages", help="list stages in canonical order")
    sub.add_parser("doctor", help="check key, models, prompt templates and schemas")
    return parser


def _make_client(factory):
    try:
        settings = Settings.from_env(ROOT)
    except MissingKeyError:
        if factory is None:
            raise
        settings = None
    return (factory or GeminiClient)(settings)


def _cmd_stages() -> int:
    for s in STAGES:
        deps = ", ".join(s.depends_on) or "—"
        print(f"{s.id:10} {s.pdlc_state:34} needs: {deps}\n{'':11}{s.question}")
    return 0


def _cmd_doctor() -> int:
    ok = all((PROMPT_DIR / f"{s.id}.md").exists() and (SCHEMA_DIR / f"{s.id}.json").exists()
             for s in STAGES)
    ready = sum((PROMPT_DIR / f"{s.id}.md").exists() for s in STAGES)
    print(f"stages:  {ready}/{len(STAGES)} prompt templates + schemas present")
    try:
        settings = Settings.from_env(ROOT)
    except MissingKeyError:
        print("api key: MISSING — set GEMINI_API_KEY in .env (copy .env.example)")
        return 1
    print(f"api key: present ({settings.api_key[:6]}…)\nresearch model:  {settings.research_model}"
          f"\nstructure model: {settings.structure_model}\ndeep agent:      {settings.deep_agent}")
    return 0 if ok else 1


def _cmd_run(args, factory) -> int:
    brief = load_brief(Path(args.idea))
    ctx = RunContext(brief=brief, out_dir=Path(args.out) / brief.slug,
                     client=_make_client(factory), deep=args.deep)
    for stage in resolve(args.stages):
        print(f"→ {stage.id}: {stage.name} …", flush=True)
        try:
            gate = run_stage(stage, ctx)["gate"]
        except MissingDependency as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"  {gate['verdict']} (score {gate['score']}) → {ctx.out_dir / stage.id}.md")
        if args.stop_on_kill and gate["verdict"] == "KILL":
            print(f"stopped: {stage.id} gate is KILL ({'; '.join(gate['reasons'])})")
            return 3
    print(f"\nreport: python -m pipeline.cli report --idea {brief.slug} --out {args.out}")
    return 0


def main(argv=None, client_factory=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "stages":
        return _cmd_stages()
    if args.command == "doctor":
        return _cmd_doctor()
    if args.command == "report":
        print(build_memo(Path(args.out) / args.idea))
        return 0
    try:
        return _cmd_run(args, client_factory)
    except MissingKeyError as exc:
        print(f"error: {exc}. Copy .env.example to .env and set GEMINI_API_KEY.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
