"""Self-validation layer: audit the pipeline's OWN output for the failures it is prone to —
over-qualification / off-ICP drift, internally inconsistent scores, KILLs resting on weak evidence,
and fabricated (unreachable) citations. All checks are deterministic; network reachability uses an
injected fetcher so tests make no real calls. Findings are advisory — they recommend reruns, they do
not silently change a gate.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_STOP = {"the", "and", "for", "ai", "startups", "startup", "saas", "inc", "llc", "a", "an", "of",
         "to", "with", "or", "builders", "agent", "agents", "company", "companies", "vertical"}
_AUDITED = ("classify", "market", "icp", "swot", "wtp", "economics", "risks", "decision")


@dataclass
class Finding:
    stage: str
    kind: str
    severity: str  # HIGH | MED | LOW
    detail: str


def _load(run_dir: Path, sid: str) -> dict:
    p = run_dir / f"{sid}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{3,}", (text or "").lower()) if w not in _STOP}


def check_off_icp(icp: dict, brief_text: str) -> list:
    """Flag a beachhead vertical whose words never appear in the brief (over-qualification / drift)."""
    vertical = ((icp.get("beachhead") or {}).get("vertical")) or ""
    vtokens = _tokens(vertical)
    if not vtokens:
        return []
    if vtokens & _tokens(brief_text):
        return []
    return [Finding("icp", "off_icp", "HIGH",
                    f"Beachhead '{vertical}' is not in the brief's actor/verticals — likely "
                    f"over-qualification. Score the founder's ICP; list this as an adjacent idea.")]


def _cheap(assumptions: list) -> bool:
    text = " ".join(str(a.get("test_cost", "")) for a in assumptions if isinstance(a, dict)).lower()
    return bool(re.search(r"[€$]0\b|\b0\b|free|1 hour|[1-9] hours", text))


def check_score_inconsistency(stage: dict) -> list:
    """Catch a score/flag that contradicts the stage's own numbers or content."""
    out = []
    gm = (stage.get("unit_economics") or {}).get("gross_margin_pct")
    if "gross_margin_below_50" in (stage.get("kill_flags") or []) and isinstance(gm, (int, float)) and gm >= 50:
        out.append(Finding(stage.get("stage", "?"), "score_inconsistency", "HIGH",
                           f"kill_flag gross_margin_below_50 but gross_margin_pct={gm} (>=50)."))
    tc = (stage.get("scores") or {}).get("test_cheapness")
    if isinstance(tc, (int, float)) and tc <= 1 and _cheap(stage.get("assumptions") or []):
        out.append(Finding(stage.get("stage", "?"), "score_inconsistency", "MED",
                           f"test_cheapness={tc} but the stage lists cheap/near-zero-cost tests."))
    return out


def check_weak_kill(stage: dict) -> list:
    """Flag a KILL / kill_flag supported only by thin, low-directness evidence."""
    gate = stage.get("gate") or {}
    if gate.get("verdict") != "KILL" and not (stage.get("kill_flags")):
        return []
    ev = stage.get("evidence") or []
    strong = [e for e in ev if isinstance(e, dict) and e.get("directness") in ("HIGH", "MED")]
    if len(strong) >= 2:
        return []
    return [Finding(stage.get("stage", "?"), "weak_kill", "HIGH",
                    f"KILL rests on {len(strong)} strong evidence item(s); verify sources before trusting it.")]


def check_citations(stage: dict, fetcher, n: int = 3) -> list:
    """Sample the first n evidence URLs; flag any the fetcher reports unreachable (fabricated citation)."""
    out = []
    urls = [e.get("source_url") for e in (stage.get("evidence") or [])
            if isinstance(e, dict) and e.get("source_url")][:n]
    for url in urls:
        if not fetcher(url):
            out.append(Finding(stage.get("stage", "?"), "citation_unreachable", "HIGH",
                               f"Evidence URL does not resolve: {url}"))
    return out


def audit(run_dir: Path, brief_text: str, fetcher=None) -> list:
    """Run every self-validation check across the run's stages; return all findings."""
    findings = check_off_icp(_load(run_dir, "icp"), brief_text)
    for sid in _AUDITED:
        stage = _load(run_dir, sid)
        if not stage:
            continue
        findings += check_score_inconsistency(stage)
        findings += check_weak_kill(stage)
        if fetcher is not None:
            findings += check_citations(stage, fetcher)
    return findings


def to_md(findings: list) -> str:
    if not findings:
        return "## Self-validation\n\nNo issues detected by the self-validation layer.\n"
    rows = "\n".join(f"- **[{f.severity}] {f.kind}** ({f.stage}): {f.detail}" for f in findings)
    return (f"## Self-validation ({len(findings)} flag(s) — advisory, verify/rerun before trusting)\n\n"
            f"{rows}\n")
