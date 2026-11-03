"""Turn a raw one-line pitch (from the hosted `validate_idea` tool) into a minimal idea brief the
pipeline can run. A hosted caller gives only a sentence, so we write the template's mandatory headings
with the pitch under 'One-sentence pitch' and let the stages fill the rest from grounded research.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path


def _slug(pitch: str) -> str:
    words = re.sub(r"[^a-z0-9\s-]", "", str(pitch).lower()).split()
    slug = "-".join(words)[:40].strip("-")
    return slug or "idea"


def _brief_md(slug: str, pitch: str) -> str:
    return (f"---\nslug: {slug}\ntitle: {pitch[:60]}\ndate: {date.today().isoformat()}\n"
            f"status: intake\n---\n\n# Idea brief\n\n## One-sentence pitch\n{pitch}\n")


def write_pitch_brief(out_root, pitch: str) -> tuple:
    slug = _slug(pitch)
    path = Path(out_root) / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_brief_md(slug, pitch))
    return slug, path
