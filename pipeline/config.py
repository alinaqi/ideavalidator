"""Settings from .env / process environment. Secrets never live in code."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULTS = {
    "GEMINI_MODEL": "gemini-3.1-pro-preview",
    "GEMINI_STRUCTURE_MODEL": "gemini-3.8-flash",
    "GEMINI_DEEP_RESEARCH_AGENT": "deep-research-preview-04-2026",
}


class MissingKeyError(RuntimeError):
    """Raised when GEMINI_API_KEY is not configured."""


def load_env(path: Path) -> dict:
    """Parse KEY=VALUE lines; comments, blanks and malformed lines are skipped."""
    if not path.exists():
        return {}
    pairs = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        pairs[key.strip()] = value.strip().strip("\"'")
    return pairs


def _lookup(key: str, file_values: dict) -> str:
    return os.environ.get(key) or file_values.get(key) or DEFAULTS.get(key, "")


@dataclass(frozen=True)
class Settings:
    api_key: str
    research_model: str
    structure_model: str
    deep_agent: str
    root: Path

    @classmethod
    def from_env(cls, root: Path) -> "Settings":
        values = load_env(root / ".env")
        key = _lookup("GEMINI_API_KEY", values)
        if not key:
            raise MissingKeyError("GEMINI_API_KEY is not set (.env or environment)")
        return cls(
            api_key=key,
            research_model=_lookup("GEMINI_MODEL", values),
            structure_model=_lookup("GEMINI_STRUCTURE_MODEL", values),
            deep_agent=_lookup("GEMINI_DEEP_RESEARCH_AGENT", values),
            root=root,
        )
