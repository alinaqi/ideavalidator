"""Helpers for reading Gemini responses: grounding sources, queries, JSON, deep-research text."""
from __future__ import annotations

import json
import re


def _web_chunks(response):
    for cand in getattr(response, "candidates", None) or []:
        meta = getattr(cand, "grounding_metadata", None)
        chunks = getattr(meta, "grounding_chunks", None) or []
        yield from (getattr(c, "web", None) for c in chunks)


def extract_sources(response) -> list:
    """Unique {url, title} pairs from grounding metadata, in citation order."""
    seen, out = set(), []
    for web in _web_chunks(response):
        uri = getattr(web, "uri", None)
        if not uri or uri in seen:
            continue
        seen.add(uri)
        out.append({"url": uri, "title": getattr(web, "title", "") or ""})
    return out


def search_queries(response) -> list:
    cands = getattr(response, "candidates", None) or []
    meta = getattr(cands[0], "grounding_metadata", None) if cands else None
    return list(getattr(meta, "web_search_queries", None) or [])


def parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model did not return valid JSON: {exc}") from exc


def deep_text(interaction) -> str:
    parts = []
    for item in getattr(interaction, "outputs", None) or []:
        text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
        if text:
            parts.append(text)
    return "\n\n".join(parts)
