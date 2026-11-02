"""Command line: `python -m pipeline.cli run|report|stages`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import MissingKeyError, Settings, make_client
from .council import CouncilContext, run_council
from .ingest import IngestRequest, build_brief
from .palgu_run import run_palgu_cmd
from .prompts import PROMPT_DIR, SCHEMA_DIR, load_brief
from .providers import Chat, load_keys
from .report_export import ReportJob, cli_report
from .runner import MissingDependency, RunContext, run_stage
from .selfcheck_run import finish_selfcheck, run_selfcheck_cmd
from .signals import SIGNAL_KEYS
from .signals_run import prep_signals, run_signals_cmd
from .stages import STAGES, resolve

ROOT = Path(__file__).resolve().parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    _add_run_report(sub)
    _add_ingest_council(sub)
    pg = sub.add_parser("palgu", help="sign up / sign in to Palgu and run on a single key")
    pg.add_argument("action", nargs="?", default="help", help="login | status | upgrade")
    sub.add_parser("stages", help="list stages in canonical order")
    sub.add_parser("doctor", help="check key, models, prompt templates and schemas")
    return parser


def _add_run_report(sub) -> None:
    run = sub.add_parser("run", help="run validation stages for an idea brief")
    run.add_argument("--idea", required=True, help="path to ideas/<slug>.md")
    run.add_argument("--stages", default="all", help="'all' or comma list of stage ids")
    run.add_argument("--out", default=str(ROOT / "runs"), help="runs directory")
    run.add_argument("--deep", action="store_true", help="use Gemini Deep Research")
    run.add_argument("--stop-on-kill", action="store_true", help="halt at first KILL gate")
    run.add_argument("--no-signals", action="store_true",
                     help="skip the demand-signal step (search volume + Reddit/X)")
    rep = sub.add_parser("report", help="export the decision report for an idea slug")
    rep.add_argument("--idea", required=True, help="idea slug (runs/<slug>)")
    rep.add_argument("--out", default=str(ROOT / "runs"))
    rep.add_argument("--format", "--output", "-output", dest="format", default="md",
                     choices=["md", "html", "xlsx", "pdf"],
                     help="md (stdout), html, xlsx, or pdf; html/pdf get Gemini imagery")
    rep.add_argument("--dest", "--out-dir", dest="dest", default="",
                     help="directory to write the report file into (default: the run folder)")


def _add_ingest_council(sub) -> None:
    ing = sub.add_parser("ingest", help="build a brief from a website URL (optionally for a new angle)")
    ing.add_argument("--url", required=True, help="business website URL to read")
    ing.add_argument("--idea", default="", help="optional angle/new idea FOR that company")
    ing.add_argument("--slug", default="", help="optional slug (else derived from domain + angle)")
    ing.add_argument("--ideas-dir", default=str(ROOT / "ideas"), help="where to write the brief")
    ing.add_argument("--out", default=str(ROOT / "runs"), help="runs directory for --run")
    ing.add_argument("--run", action="store_true", help="run the full pipeline after ingesting")
    sig = sub.add_parser("signals", help="demand signals: search volume + Reddit/X validation")
    sig.add_argument("--idea", required=True, help="path to ideas/<slug>.md")
    sig.add_argument("--out", default=str(ROOT / "runs"))
    sc = sub.add_parser("selfcheck", help="self-validation audit of a completed run")
    sc.add_argument("--idea", required=True, help="path to ideas/<slug>.md")
    sc.add_argument("--out", default=str(ROOT / "runs"))
    council = sub.add_parser("council", help="multi-model sounding board debate on an idea")
    council.add_argument("--idea", required=True, help="path to ideas/<slug>.md")
    council.add_argument("--out", default=str(ROOT / "runs"))
    council.add_argument("--rounds", type=int, default=1, help="debate rounds (0-2)")
    council.add_argument("--no-red-team", action="store_true")


def _make_client(factory):
    try:
        settings = Settings.from_env(ROOT)
    except MissingKeyError:
        if factory is None:
            raise
        settings = None
    return factory(settings) if factory else make_client(settings)


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
        print("api key: MISSING — set GEMINI_API_KEY in .env, or run `palgu login` for a single Palgu key")
        return 1
    print(f"provider: {settings.provider}" + (" (Palgu gateway)" if settings.provider == "palgu" else ""))
    sk = load_keys(ROOT, SIGNAL_KEYS)
    srcs = [n for n, on in (("dataforseo", sk.get("DATAFORSEO_LOGIN") and sk.get("DATAFORSEO_PASSWORD")),
                            ("reddit", sk.get("REDDIT_CLIENT_ID") and sk.get("REDDIT_CLIENT_SECRET")),
                            ("apify", sk.get("APIFY_TOKEN")), ("grok-x", sk.get("XAI_API_KEY"))) if on]
    print(f"api key: present ({settings.api_key[:6]}…)\nresearch model:  {settings.research_model}"
          f"\nstructure model: {settings.structure_model}\ndeep agent:      {settings.deep_agent}"
          f"\ncouncil models:  {', '.join(Chat(load_keys(ROOT)).available()) or 'none (optional)'}"
          f"\nsignal sources:  {', '.join(srcs) or 'none (optional)'}")
    return 0 if ok else 1


def _cmd_ingest(args, factory) -> int:
    client = _make_client(factory)
    slug, md = build_brief(client, IngestRequest(args.url, args.idea, args.slug))
    path = Path(args.ideas_dir) / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md)
    print(f"ingested {args.url} -> {path}")
    if args.run:
        ns = argparse.Namespace(idea=str(path), stages="all", out=args.out,
                                deep=False, stop_on_kill=False, no_signals=False)
        return _cmd_run(ns, factory)
    print(f"next: python -m pipeline.cli run --idea {path}")
    return 0


def _cmd_council(args, factories: tuple) -> int:
    brief = load_brief(Path(args.idea))
    chat = (factories[1] or Chat)(load_keys(ROOT))
    ctx = CouncilContext(brief=brief, out_dir=Path(args.out) / brief.slug, chat=chat,
                         structurer=_make_client(factories[0]).structure,
                         rounds=min(2, max(0, args.rounds)), red_team=not args.no_red_team)
    print(f"→ council: {', '.join(chat.available()) or 'no models'} …", flush=True)
    data = run_council(ctx)
    rec = data["synthesis"].get("recommendation") or {}
    votes = ", ".join(f"{v.get('role')}={v.get('vote')}" for v in data["synthesis"].get("votes") or [])
    print(f"  {rec.get('verdict', 'UNKNOWN')} — {rec.get('rationale', '')[:200]}\n  votes: {votes}"
          f"\n  → {ctx.out_dir / 'council.md'}")
    return 0


def _cmd_run(args, factory) -> int:
    brief = load_brief(Path(args.idea))
    ctx = RunContext(brief=brief, out_dir=Path(args.out) / brief.slug,
                     client=_make_client(factory), deep=args.deep)
    if not getattr(args, "no_signals", False):
        prep_signals(ctx, load_keys(ROOT, SIGNAL_KEYS))
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
    finish_selfcheck(brief, ctx.out_dir)
    print(f"\nreport: python -m pipeline.cli report --idea {brief.slug} --out {args.out}")
    return 0


def main(argv=None, client_factory=None, chat_factory=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "palgu":
        return run_palgu_cmd(args, ROOT)
    if args.command == "stages":
        return _cmd_stages()
    if args.command == "doctor":
        return _cmd_doctor()
    if args.command == "council":
        return _cmd_council(args, (client_factory, chat_factory))
    if args.command == "ingest":
        return _cmd_ingest(args, client_factory)
    if args.command == "signals":
        return run_signals_cmd(args, ROOT)
    if args.command == "selfcheck":
        return run_selfcheck_cmd(args, ROOT)
    if args.command == "report":
        job = ReportJob(run_dir=Path(args.out) / args.idea, fmt=args.format,
                        dest=Path(args.dest) if args.dest else None, root=ROOT)
        print(cli_report(job))
        return 0
    try:
        return _cmd_run(args, client_factory)
    except MissingKeyError as exc:
        print(f"error: {exc}. Copy .env.example to .env and set GEMINI_API_KEY.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
