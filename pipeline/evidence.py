"""Evidence records with Palgu PDLC quality labels (Evidence Quality sheet)."""
from __future__ import annotations

from urllib.parse import urlparse

ENUMS = {
    "directness": ("HIGH", "MED", "LOW"),
    "behavior_vs_stated": ("BEHAVIOR", "STATED", "MIXED"),
    "recency": ("FRESH", "STALE"),
}
SOURCE_TYPES = ("forum", "review", "job_post", "pricing_page", "report", "news",
                "official_doc", "competitor_site", "search_data", "academic",
                "interview", "sales_signal", "other")
WEIGHTS = {
    "directness": {"HIGH": 3, "MED": 2, "LOW": 0},
    "behavior_vs_stated": {"BEHAVIOR": 3, "MIXED": 2, "STATED": 0},
    "recency": {"FRESH": 2, "STALE": 0},
}
UNKNOWN_WEIGHT = 1


def _enum(value, allowed: tuple) -> str:
    text = str(value or "").strip().upper()
    return text if text in allowed else "UNKNOWN"


def _domain(url: str) -> str:
    host = urlparse(url or "").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def normalize(record: dict) -> dict:
    """Coerce a raw evidence dict into the canonical labelled shape."""
    claim = str(record.get("claim") or "").strip()
    if not claim:
        raise ValueError("evidence record needs a non-empty 'claim'")
    url = str(record.get("source_url") or "").strip()
    source_type = str(record.get("source_type") or "").lower()
    out = {
        "claim": claim,
        "source_url": url,
        "source_type": source_type if source_type in SOURCE_TYPES else "other",
    }
    for field, allowed in ENUMS.items():
        out[field] = _enum(record.get(field), allowed)
    out["independence_group"] = (
        str(record.get("independence_group") or "").strip() or _domain(url) or "unknown"
    )
    return out


def score(record: dict) -> int:
    """0 (weak, stated, stale) .. 8 (direct, behavioural, fresh)."""
    return sum(WEIGHTS[f].get(record.get(f), UNKNOWN_WEIGHT) for f in WEIGHTS)


def _label(count: int, groups: int) -> str:
    if count == 0:
        return "NONE"
    if groups >= 3:
        return "STRONG"
    return "MEDIUM" if groups == 2 else "WEAK"


def triangulate(records: list) -> dict:
    """Source-independence summary: how many distinct origins agree."""
    groups = {r.get("independence_group") or "unknown" for r in records}
    mean = round(sum(score(r) for r in records) / len(records), 2) if records else 0.0
    return {
        "records": len(records),
        "independent_groups": len(groups),
        "mean_score": mean,
        "label": _label(len(records), len(groups)),
    }
