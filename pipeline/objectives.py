"""Success-definition objectives: make gates and prompts flexible to the kind of business intended.

A direct-sales SMB SaaS, a PLG/freemium directory, a services cash business and a venture-scale
network are different games. The same idea can pass one and fail another. The objective reweights
what counts as a hard-KILL (e.g. low immediate per-user willingness-to-pay does not kill a PLG/graph
thesis whose economics rest on a paying fraction of a large free base) and injects model guidance."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Objective:
    key: str
    label: str
    aliases: tuple
    guidance: str
    demote_critical: dict = field(default_factory=dict)


_LIST = (
    Objective(
        "default", "Default (profitable-from-day-one, founder-led)", (),
        "No business-model override: judge against direct founder-led sales, where immediate paid "
        "conversion is the key signal.", {}),
    Objective(
        "services_cash", "Services / cash now",
        ("services", "cash now", "services / cash now", "consulting", "agency", "productised service"),
        "This is a services/cash business. Optimise for immediate paid delivery and founder-hour "
        "economics. Say plainly if it is a well-paid job rather than a scalable company.", {}),
    Objective(
        "compounding_product", "Compounding product (defensible asset)",
        ("compounding", "product", "compounding product", "moat", "defensible", "saas product"),
        "This is a compounding-product bet: the point is an asset that gets harder to copy over time "
        "(graph, data, network, integrations). Low immediate per-user willingness-to-pay is NOT fatal "
        "if the moat and funnel logic hold; the riskiest thing to test is the core mechanism and the "
        "acquisition loop, not a two-week pre-sale. Size by funnel and paying fraction, not outbound.",
        {"wtp": ("budget_exists",), "economics": ("breakeven_reachability",),
         "market": ("market_pull",)}),
    Objective(
        "plg_network", "PLG / freemium / directory / network",
        ("plg", "freemium", "directory", "network", "marketplace", "graph", "plg / network",
         "plg_freemium", "plg_freemium_directory", "two-sided", "two sided"),
        "This is a product-led / directory / network model. Most users are free; revenue comes from a "
        "small paying fraction of a large base, and value compounds with coverage and network effects. "
        "Do NOT size it as an outbound SMB sales motion or kill it on low per-user WTP. Size by the "
        "funnel: reachable base -> listed/profiled -> claimed -> activated -> paid, and judge whether a "
        "few percent paying clears the floor. The key tests are claim-rate and activation, not a pre-sale.",
        {"wtp": ("budget_exists", "margin_room"),
         "economics": ("breakeven_reachability",), "market": ("market_pull",)}),
    Objective(
        "venture_scale", "Venture-scale",
        ("venture", "vc", "venture scale", "venture-scale", "fund"),
        "This is a venture-scale bet: judge market size, defensibility and a path to a very large "
        "outcome. Immediate day-one profit matters less than a credible route to scale and a moat.",
        {"economics": ("breakeven_reachability",)}),
)

OBJECTIVES = {o.key: o for o in _LIST}


def resolve(brief) -> Objective:
    """Pick the objective from the brief's success_definition (token or alias); default if unknown."""
    raw = (getattr(brief, "success_definition", "") or "").strip().lower()
    if not raw:
        return OBJECTIVES["default"]
    for obj in _LIST:
        if raw == obj.key or raw in obj.aliases or any(a in raw for a in obj.aliases):
            return obj
    return OBJECTIVES["default"]


def guidance(key: str) -> str:
    obj = OBJECTIVES.get(key)
    return obj.guidance if obj else ""


def demotions(key: str, stage_id: str) -> tuple:
    obj = OBJECTIVES.get(key)
    return obj.demote_critical.get(stage_id, ()) if obj else ()
