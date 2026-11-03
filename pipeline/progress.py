"""Lightweight per-run progress file so a live status-line mod can show how far a validation has got.
`run` writes `runs/<slug>/progress.json` before and after each stage; the mod reads the newest one.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ProgressStep:
    index: int
    total: int
    stage: str
    state: str = "running"   # running | done | complete
    verdict: str = ""
    score: float = 0.0


def write_progress(out_dir, step: ProgressStep) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = asdict(step)
    data["ts"] = time.time()
    (out / "progress.json").write_text(json.dumps(data))
