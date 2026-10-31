"""Idea briefs, prompt templates and output schemas."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"
SCHEMA_DIR = Path(__file__).parent / "schemas"


@dataclass
class Brief:
    slug: str
    title: str
    body: str
    meta: dict = field(default_factory=dict)
    business_model: str = ""
    success_definition: str = ""


def _split_frontmatter(text: str) -> tuple:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta, parts[2].lstrip("\n")


def load_brief(path: Path) -> Brief:
    meta, body = _split_frontmatter(path.read_text())
    slug = meta.get("slug") or path.stem
    return Brief(slug=slug, title=meta.get("title") or slug, body=body, meta=meta,
                 business_model=meta.get("business_model", ""),
                 success_definition=meta.get("success_definition", ""))


def prior_block(prior: dict) -> str:
    if not prior:
        return "(no prior stages; this is the first stage)"
    return "\n\n".join(f"### Prior stage `{k}` summary\n{v}" for k, v in prior.items())


def _replacements(stage, brief: Brief, prior: dict) -> dict:
    from .objectives import guidance, resolve

    objective = resolve(brief)
    return {
        "{{common}}": (PROMPT_DIR / "_common.md").read_text().strip(),
        "{{business_model}}": brief.business_model or "UNKNOWN (classify it in this stage)",
        "{{success_definition}}": brief.success_definition or f"UNKNOWN -> treat as {objective.label}",
        "{{success_guidance}}": f"{objective.label}: {guidance(objective.key)}",
        "{{title}}": brief.title,
        "{{brief}}": brief.body.strip(),
        "{{prior}}": prior_block(prior),
        "{{today}}": date.today().isoformat(),
        "{{stage_question}}": stage.question,
        "{{pdlc_state}}": stage.pdlc_state,
    }


def render(stage, brief: Brief, prior: dict) -> str:
    """Fill the stage template with the brief and prior-stage summaries."""
    template_path = PROMPT_DIR / f"{stage.id}.md"
    if not template_path.exists():
        raise FileNotFoundError(f"no prompt template for stage '{stage.id}'")
    text = template_path.read_text()
    for token, value in _replacements(stage, brief, prior).items():
        text = text.replace(token, value)
    return text


def load_schema(stage) -> dict:
    return json.loads((SCHEMA_DIR / f"{stage.id}.json").read_text())
