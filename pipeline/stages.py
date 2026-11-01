"""Canonical validation stages and their mapping to Palgu PDLC states."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    id: str
    name: str
    pdlc_state: str
    depends_on: tuple
    question: str
    optional: tuple = ()


_CORE = ("frame", "problem", "market", "icp", "swot", "wtp", "economics", "risks")

STAGES = (
    Stage("frame", "Frame the opportunity", "S1 FRAME", (),
          "Is this a solution-independent opportunity for a specific actor, "
          "and what must be true for it to work?"),
    Stage("classify", "Classify category, business model and USP", "S1 FRAME", ("frame",),
          "What business category is this (so we compare to the right incumbents), which business "
          "models could it use, and what is the Business Model Canvas and USP?"),
    Stage("problem", "Validate the problem", "S1 FRAME", ("frame",),
          "Does the problem exist, recur, and already cost people money or "
          "behaviour change?"),
    Stage("market", "Understand the market", "S1-S2 FRAME/EXPLORE",
          ("frame", "problem"),
          "What do buyers do today, who competes, how big is the reachable "
          "market, and what is shifting?"),
    Stage("icp", "Identify ICP and beachhead vertical", "S1-S3 FRAME→DE-RISK",
          ("frame", "problem", "market"),
          "Which narrow segment has the most urgent, best-funded, most "
          "reachable version of the problem?"),
    Stage("swot", "SWOT / TOWS matrix", "S2 EXPLORE", ("market", "icp"),
          "For the chosen beachhead, where are we strong or weak, and what "
          "must we exploit or defend?"),
    Stage("wtp", "Validate willingness to pay", "S3 DE-RISK (value/viability)",
          ("problem", "market", "icp"),
          "What do comparable buyers already pay, for which value metric, and "
          "how do we test it behaviourally?"),
    Stage("economics", "Day-one profitability model", "S3 DE-RISK (viability)",
          ("icp", "wtp"),
          "How many customers, at what price and acquisition cost, make this "
          "profitable from month one?"),
    Stage("risks", "Assumption and risk map", "S3 DE-RISK",
          ("problem", "market", "icp", "wtp", "economics"),
          "Which value/usability/feasibility/viability assumptions are "
          "important and weakly evidenced, and what is the smallest test?"),
    Stage("decision", "Decision memo and bet record", "S3→S4 SHAPE / Bet Portfolio",
          _CORE,
          "GO, PIVOT or KILL, with kill conditions and the next two weeks of "
          "real-world tests?", optional=("council",)),
)

_BY_ID = {s.id: s for s in STAGES}


def stage_ids() -> list:
    return [s.id for s in STAGES]


def get_stage(stage_id: str) -> Stage:
    return _BY_ID[stage_id]


def resolve(selection: str) -> list:
    """'all' or a comma list of ids, returned in canonical order."""
    if selection.strip() == "all":
        return list(STAGES)
    wanted = {part.strip() for part in selection.split(",") if part.strip()}
    unknown = wanted - set(_BY_ID)
    if unknown:
        raise ValueError(f"unknown stage(s): {sorted(unknown)}; valid: {stage_ids()}")
    return [s for s in STAGES if s.id in wanted]
