"""CLI-facing report export: choose a format, wire optional Gemini imagery, and place the
produced file in a caller-chosen destination directory (defaults to the run folder)."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .report import build_memo
from .report_formats import export


@dataclass
class ReportJob:
    run_dir: Path
    fmt: str = "md"
    dest: Path | None = None  # directory to write the report file into; None = run_dir
    root: Path | None = None  # repo root, used to find GEMINI_API_KEY for html/pdf imagery


def _settings_for(job: ReportJob):
    """Settings for html/pdf imagery, or None when no key / not an image format."""
    from .config import MissingKeyError, Settings

    if job.root is None or job.fmt not in ("html", "pdf"):
        return None
    try:
        return Settings.from_env(Path(job.root))
    except MissingKeyError:
        return None


def _place(produced: Path, dest: Path | None) -> Path:
    """Copy the produced report into `dest`; no-op when dest is unset or already the source dir."""
    if dest is None or Path(dest) == produced.parent:
        return produced
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / produced.name
    shutil.copy2(produced, target)
    return target


def export_with_images(job: ReportJob) -> Path:
    """export() with a Gemini hero image for html/pdf, then placed into job.dest."""
    from .images import generate_hero

    settings = _settings_for(job)
    image_fn = (lambda slug: generate_hero(slug, settings=settings)) if settings else None
    produced = export(job.run_dir, job.fmt, image_fn=image_fn)
    return _place(produced, job.dest)


def cli_report(job: ReportJob) -> str:
    """Text the CLI prints: the memo for md-to-stdout, else a 'wrote <path>' line."""
    if job.fmt == "md" and job.dest is None:
        return build_memo(job.run_dir)
    return f"wrote {export_with_images(job)}"
