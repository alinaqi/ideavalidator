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
    provider: str = "gemini"      # "gemini" (own key) or "palgu" (single Palgu key)
    palgu_base: str = ""

    @classmethod
    def _gemini(cls, key: str, values: dict, root: Path) -> "Settings":
        return cls(api_key=key, research_model=_lookup("GEMINI_MODEL", values),
                   structure_model=_lookup("GEMINI_STRUCTURE_MODEL", values),
                   deep_agent=_lookup("GEMINI_DEEP_RESEARCH_AGENT", values), root=root)

    @classmethod
    def _palgu(cls, key: str, values: dict, root: Path) -> "Settings":
        return cls(api_key=key, provider="palgu",
                   palgu_base=_lookup("PALGU_GATEWAY", values) or "https://api.palgu.ai/v1",
                   research_model=_lookup("PALGU_MODEL", values) or "gemini-3.8-flash",
                   structure_model=_lookup("PALGU_STRUCTURE_MODEL", values) or "gemini-3.8-flash",
                   deep_agent="", root=root)

    @classmethod
    def from_env(cls, root: Path) -> "Settings":
        """Prefer an explicit GEMINI_API_KEY (full grounding); else a Palgu key (single-key easy mode)."""
        values = load_env(root / ".env")
        gemini = _lookup("GEMINI_API_KEY", values)
        if gemini:
            return cls._gemini(gemini, values, root)
        palgu = _lookup("PALGU_API_KEY", values)
        if palgu:
            return cls._palgu(palgu, values, root)
        raise MissingKeyError("set GEMINI_API_KEY or PALGU_API_KEY (or run `palgu login`)")


def make_client(settings: Settings):
    """Return the pipeline client for the configured provider."""
    if settings.provider == "palgu":
        from .palgu_client import PalguClient
        return PalguClient(settings)
    from .gemini import GeminiClient
    return GeminiClient(settings)
