"""Glue for the self-validation layer: a conservative URL-reachability fetcher, persistence, and the
CLI/end-of-run entry points. Reachability flags only definitive 404/410 so legitimate redirects are not
false-flagged."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path

from . import selfcheck
from .prompts import load_brief


def reachable(url: str) -> bool:
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method,
                                         headers={"User-Agent": "ideavalidator/0.1"})
            with urllib.request.urlopen(req, timeout=15):
                return True
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                return False
            if method == "GET":
                return True
        except Exception:
            if method == "GET":
                return True
    return True


def write_selfcheck(run_dir: Path, findings: list) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "selfcheck.json").write_text(json.dumps([asdict(f) for f in findings], indent=2))
    (run_dir / "selfcheck.md").write_text(selfcheck.to_md(findings))
    return run_dir / "selfcheck.md"


def finish_selfcheck(brief, out_dir: Path, fetcher=None) -> list:
    findings = selfcheck.audit(out_dir, brief.body, fetcher=fetcher or reachable)
    write_selfcheck(out_dir, findings)
    print(f"self-validation: {len(findings)} flag(s) → {out_dir / 'selfcheck.md'}")
    return findings


def run_selfcheck_cmd(args, root: Path) -> int:
    brief = load_brief(Path(args.idea))
    finish_selfcheck(brief, Path(args.out) / brief.slug)
    return 0
