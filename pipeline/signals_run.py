"""Glue between the pipeline/CLI and the demand-signal engine: gather once, persist, stamp the bonus."""
from __future__ import annotations

import json
from pathlib import Path

from . import signals, signals_sources
from .prompts import load_brief


def write_signals(out_dir: Path, ds) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "signals.json").write_text(json.dumps(signals.to_dict(ds), indent=2, ensure_ascii=False))
    (out_dir / "signals.md").write_text(ds.summary)
    return out_dir / "signals.json"


def prep_signals(ctx, keys: dict):
    """Gather signals for a run, write them, and stamp the bonus + summary onto the RunContext."""
    ds = signals.gather(ctx.brief, keys, signals_sources.default_fetchers())
    write_signals(ctx.out_dir, ds)
    ctx.signal_bonus = ds.bonus
    ctx.signals_summary = ds.summary
    return ds


def run_signals_cmd(args, root: Path) -> int:
    from .providers import load_keys

    brief = load_brief(Path(args.idea))
    keys = load_keys(root, signals.SIGNAL_KEYS)
    ds = signals.gather(brief, keys, signals_sources.default_fetchers())
    out = write_signals(Path(args.out) / brief.slug, ds)
    print(f"signals: bonus +{ds.bonus:g} ({len(ds.search)} search, {len(ds.social)} social) → {out}")
    return 0
