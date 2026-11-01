"""Demand signals: search-volume and social-validation evidence for an idea.

Signals are ADDITIVE — their presence earns a small, capped confidence bonus; their absence never
penalises an idea (missing signals are common for genuinely new markets). Every source is best-effort:
a missing key or any error yields no signal, not a failure. Scoring here is pure and deterministic;
the real network clients live in `signals_sources`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

# Keys read (via providers.load_keys) to power the sources. DataForSEO = search volume;
# Apify/xAI = Reddit/X listening. Zernio is a publishing API, not a listening one — not used here.
SIGNAL_KEYS = ("DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD", "APIFY_TOKEN", "XAI_API_KEY")
MAX_BONUS = 0.5


@dataclass
class Signal:
    source: str          # dataforseo | apify | grok
    kind: str            # search_volume | social
    label: str           # keyword or thread title
    value: float | None  # monthly volume, or mention/upvote count
    detail: str = ""
    url: str = ""


@dataclass
class DemandSignals:
    query: str
    search: list = field(default_factory=list)
    social: list = field(default_factory=list)
    score: float = 0.0   # 0..1, bonus / MAX_BONUS
    bonus: float = 0.0    # 0..MAX_BONUS, added to market/problem/decision verdicts
    summary: str = ""


def keywords_for(brief) -> list:
    """Short keyword list to probe: the cleaned title plus any meta keywords (deduped, max 5)."""
    title = (brief.title or brief.slug or "").split("—")[-1].split(" - ")[-1].strip()
    extra = [k.strip() for k in str(brief.meta.get("candidate_keywords", "")).split(",") if k.strip()]
    out = []
    for kw in [title, *extra, brief.slug.replace("-", " ")]:
        low = kw.lower().strip()
        if low and low not in out:
            out.append(low)
    return out[:5]


def _tier(value: float, high: float, mid: float) -> float:
    if value >= high:
        return 0.25
    if value >= mid:
        return 0.15
    return 0.05 if value > 0 else 0.0


def compute_bonus(search: list, social: list) -> tuple:
    """Deterministic (score, bonus). Strong search volume and social chatter each add up to 0.25."""
    volume = max((s.value or 0 for s in search), default=0)
    mentions = sum((s.value or 1) for s in social)
    bonus = round(min(MAX_BONUS, _tier(volume, 1000, 100) + _tier(mentions, 10, 3)), 2)
    return round(bonus / MAX_BONUS, 2), bonus


def summarize(ds: DemandSignals) -> str:
    """Compact text for prompts and the memo; empty sources read as explicit UNKNOWN, not a negative."""
    vol = "; ".join(f"{s.label}: {int(s.value or 0)}/mo" for s in ds.search) or "no search-volume data"
    soc = "; ".join(f"{s.label} ({s.source})" for s in ds.social[:5]) or "no social mentions found"
    return (f"Demand signals for '{ds.query}' (bonus +{ds.bonus:g}):\n"
            f"- Search volume: {vol}\n- Social validation: {soc}\n"
            f"(Absence is not evidence against the idea.)")


def _safe(fn, *args) -> list:
    try:
        return list(fn(*args) or [])
    except Exception:
        return []


def gather(brief, keys: dict, fetchers) -> DemandSignals:
    """Collect search + social signals best-effort and attach the capped bonus and a summary."""
    kws = keywords_for(brief)
    query = kws[0] if kws else (brief.title or brief.slug)
    search = _safe(fetchers.search_volume, kws, keys)
    social = _safe(fetchers.social, query, keys)
    score, bonus = compute_bonus(search, social)
    ds = DemandSignals(query=query, search=search, social=social, score=score, bonus=bonus)
    ds.summary = summarize(ds)
    return ds


def to_dict(ds: DemandSignals) -> dict:
    return asdict(ds)


def from_dict(data: dict) -> DemandSignals:
    mk = lambda items: [Signal(**s) for s in items or []]
    return DemandSignals(query=data.get("query", ""), search=mk(data.get("search")),
                         social=mk(data.get("social")), score=data.get("score", 0.0),
                         bonus=data.get("bonus", 0.0), summary=data.get("summary", ""))
