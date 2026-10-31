"""Validation modes: innovative, new-category ideas need a different evidence regime.

The default pipeline rewards existing demand (behaviour, prior spend, incumbent pricing, search
volume). A genuine blue-ocean idea has none of that yet — absence of competitors and absence of
existing spend are EXPECTED, not disqualifying. `new_market` mode stops novelty being scored as
no-demand: it demotes the existing-market criticals and tells every stage to use analog/proxy
evidence plus a designed demand-creation test instead of looking for people already paying."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Mode:
    key: str
    label: str
    aliases: tuple
    guidance: str
    demote_critical: dict = field(default_factory=dict)


_LIST = (
    Mode(
        "existing_market", "Existing market (validate against current demand)", (),
        "Standard regime: an observable market exists; weigh existing behaviour, spend and incumbents.",
        {}),
    Mode(
        "new_market", "New market / innovation (create demand, think out of the box)",
        ("new_market", "innovation", "innovative", "new market", "novel", "blue ocean", "blue_ocean",
         "create demand", "demand creation", "category creation", "zero to one", "0 to 1"),
        "This is an out-of-the-box / new-category idea; validate it DIFFERENTLY. Absence of competitors, "
        "search volume or existing spend is a SIGNAL about novelty, NOT proof of no demand — never score "
        "it as 'no market' or raise market-too-small/dominant-incumbent flags on CURRENT size alone; "
        "judge the market the idea could CREATE. A vision-led or solution-first idea is legitimate here, "
        "so do not auto-fire 'solution in search of a problem' — instead require a credible, dated "
        "why-now and a cheap DESIGNED test. Evidence comes from analogies/proxies (adjacent behaviours, "
        "how people hack the job today, prior category-creation precedents) plus a demand-creation "
        "experiment: Savoia pretotype / XYZ 'The Right It' hypothesis, fake-door, landing page + "
        "waitlist, Wizard-of-Oz, concierge, or pre-order with a PRE-REGISTERED signal. The riskiest "
        "assumption is 'will anyone want this at all', tested by manufacturing a real behavioural signal "
        "for something that does not exist yet — not by finding people already paying.",
        {"problem": ("existing_spend",), "market": ("market_pull",)}),
)

MODES = {m.key: m for m in _LIST}


def resolve(brief) -> Mode:
    raw = (getattr(brief, "validation_mode", "") or "").strip().lower()
    if not raw:
        return MODES["existing_market"]
    for mode in _LIST:
        if raw == mode.key or raw in mode.aliases or any(a in raw for a in mode.aliases):
            return mode
    return MODES["existing_market"]


def guidance(key: str) -> str:
    mode = MODES.get(key)
    return mode.guidance if mode else ""


def demotions(key: str, stage_id: str) -> tuple:
    mode = MODES.get(key)
    return mode.demote_critical.get(stage_id, ()) if mode else ()
