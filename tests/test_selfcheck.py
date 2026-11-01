import json

from pipeline.selfcheck import (Finding, audit, check_citations, check_off_icp,
                                check_score_inconsistency, check_weak_kill, to_md)


def test_off_icp_flags_vertical_not_in_brief():
    icp = {"beachhead": {"vertical": "Healthcare / Dental AI Agent Startups"}}
    brief = "A personal calling MCP that lets your AI assistant book restaurants and appointments."
    f = check_off_icp(icp, brief)
    assert f and f[0].kind == "off_icp" and f[0].severity == "HIGH"


def test_off_icp_ok_when_in_brief():
    icp = {"beachhead": {"vertical": "Indie hackers building AI agents"}}
    brief = "A connector for indie hackers who build AI agents and want calling."
    assert check_off_icp(icp, brief) == []


def test_score_inconsistency_gross_margin_flag_vs_value():
    econ = {"stage": "economics", "kill_flags": ["gross_margin_below_50"],
            "unit_economics": {"gross_margin_pct": 58.8}}
    f = check_score_inconsistency(econ)
    assert any(x.kind == "score_inconsistency" for x in f)


def test_score_inconsistency_cheap_tests_but_zero_cheapness():
    risks = {"stage": "risks", "scores": {"test_cheapness": 0},
             "assumptions": [{"test_cost": "10 hours, €0"}]}
    f = check_score_inconsistency(risks)
    assert any(x.kind == "score_inconsistency" for x in f)


def test_weak_kill_flags_single_low_directness():
    stage = {"stage": "swot", "gate": {"verdict": "KILL"},
             "evidence": [{"claim": "incumbent bundles", "directness": "LOW"}]}
    assert any(x.kind == "weak_kill" for x in check_weak_kill(stage))


def test_weak_kill_ok_with_strong_evidence():
    stage = {"stage": "swot", "gate": {"verdict": "KILL"}, "evidence": [
        {"claim": "a", "directness": "HIGH"}, {"claim": "b", "directness": "HIGH"}]}
    assert check_weak_kill(stage) == []


def test_check_citations_flags_unreachable():
    stage = {"stage": "market", "evidence": [
        {"claim": "x", "source_url": "https://ok.example/a"},
        {"claim": "y", "source_url": "https://dead.example/b"}]}
    reachable = {"https://ok.example/a": True, "https://dead.example/b": False}
    f = check_citations(stage, fetcher=lambda u: reachable.get(u, False), n=3)
    assert any(x.kind == "citation_unreachable" and "dead.example" in x.detail for x in f)


def test_audit_aggregates_and_to_md(tmp_path):
    (tmp_path / "icp.json").write_text(json.dumps(
        {"beachhead": {"vertical": "Healthcare AI startups"}}))
    (tmp_path / "economics.json").write_text(json.dumps(
        {"stage": "economics", "kill_flags": ["gross_margin_below_50"],
         "unit_economics": {"gross_margin_pct": 70}}))
    findings = audit(tmp_path, "a personal calling tool", fetcher=lambda u: True)
    assert findings
    md = to_md(findings)
    assert "Self-validation" in md and "off_icp" in md
