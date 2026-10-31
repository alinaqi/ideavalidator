"""Deterministic GO / PIVOT / KILL gates computed from stage scores (0-5)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GateRule:
    criteria: tuple
    critical: tuple = ()
    go_threshold: float = 3.5
    pivot_threshold: float = 2.5


@dataclass
class Gate:
    stage: str
    verdict: str
    score: float
    reasons: list = field(default_factory=list)


RULES = {
    "frame": GateRule(("actor_specificity", "job_clarity", "solution_independence",
                       "why_now", "why_us"), ("actor_specificity",)),
    "problem": GateRule(("problem_evidence", "frequency", "severity",
                         "existing_spend", "urgency"),
                        ("problem_evidence", "existing_spend")),
    "market": GateRule(("market_pull", "reachable_market_size",
                        "competitive_whitespace", "trend_tailwind",
                        "regulatory_feasibility"), ("market_pull",)),
    "icp": GateRule(("beachhead_clarity", "pain_urgency", "budget_authority",
                     "reachability", "segment_homogeneity"),
                    ("reachability", "budget_authority")),
    "swot": GateRule(("strength_leverage", "weakness_manageability",
                      "opportunity_size", "threat_tolerance")),
    "wtp": GateRule(("price_comparables", "value_metric_clarity", "budget_exists",
                     "behavioral_signal", "margin_room"),
                    ("budget_exists", "margin_room")),
    "economics": GateRule(("breakeven_reachability", "cac_payback", "gross_margin",
                           "time_to_first_revenue", "founder_capacity_fit"),
                          ("breakeven_reachability", "gross_margin")),
    "risks": GateRule(("value_risk_coverage", "viability_risk_coverage",
                       "feasibility_risk_coverage", "test_cheapness")),
    "decision": GateRule(("evidence_strength", "profitability_confidence",
                          "focus_clarity", "execution_readiness"),
                         ("evidence_strength",)),
}

_PRECEDENCE = ("KILL", "UNKNOWN", "PIVOT", "GO")


def _usable_scores(output: dict, rule: GateRule) -> dict:
    raw = output.get("scores") or {}
    scores = {}
    for name in rule.criteria:
        value = raw.get(name)
        if isinstance(value, (int, float)):
            scores[name] = max(0.0, min(5.0, float(value)))
    return scores


def _effective_critical(stage_id: str, rule: GateRule, output: dict) -> tuple:
    """Critical criteria after the objective's demotions (business-model flexibility)."""
    from .objectives import demotions

    demoted = set(demotions(output.get("objective", ""), stage_id))
    return tuple(c for c in rule.critical if c not in demoted)


def _kill_reasons(output: dict, scores: dict, critical: tuple) -> list:
    reasons = [f"kill flag: {flag}" for flag in output.get("kill_flags") or []]
    for name in critical:
        if scores.get(name, 5.0) < 2:
            reasons.append(f"critical criterion '{name}' scored {scores[name]:g} (<2)")
    return reasons


def _verdict(avg: float, rule: GateRule, floor_ok: bool) -> str:
    if avg >= rule.go_threshold and floor_ok:
        return "GO"
    return "PIVOT" if avg >= rule.pivot_threshold else "KILL"


def evaluate(stage_id: str, output: dict) -> Gate:
    """Score a stage's structured output; KILL flags and critical floors dominate."""
    rule = RULES[stage_id]
    scores = _usable_scores(output, rule)
    if not scores:
        return Gate(stage_id, "UNKNOWN", 0.0, ["no usable scores in output"])
    avg = round(sum(scores.values()) / len(scores), 2)
    reasons = _kill_reasons(output, scores, _effective_critical(stage_id, rule, output))
    if reasons:
        return Gate(stage_id, "KILL", avg, reasons)
    floor_ok = min(scores.values()) >= 2
    verdict = _verdict(avg, rule, floor_ok)
    notes = [f"mean {avg:g} over {len(scores)} criteria"]
    if not floor_ok:
        notes.append("a criterion scored below 2, capped at PIVOT")
    return Gate(stage_id, verdict, avg, notes)


def rollup(gates: list) -> Gate:
    """Overall verdict: KILL > UNKNOWN > PIVOT > GO."""
    if not gates:
        return Gate("overall", "UNKNOWN", 0.0, ["no stages run"])
    verdicts = {g.verdict for g in gates}
    verdict = next(v for v in _PRECEDENCE if v in verdicts)
    avg = round(sum(g.score for g in gates) / len(gates), 2)
    return Gate("overall", verdict, avg, [f"{g.stage}: {g.verdict}" for g in gates])
