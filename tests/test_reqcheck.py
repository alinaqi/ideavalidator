"""Pure requirements-check logic: request validation, prompt, normalisation and verdict (contract v1)."""
import pytest

from pipeline import reqcheck as rc
from tests.reqcheck_fixtures import invalid_bodies, load


@pytest.mark.parametrize("name,body", invalid_bodies())
def test_invalid_bodies_are_rejected(name, body):
    assert rc.validate_request(body), name


@pytest.mark.parametrize("name", ["request_wrong.json", "request_ok.json"])
def test_valid_bodies_pass(name):
    assert rc.validate_request(load(name)) == []


def test_depth_defaults_to_quick_and_context_is_optional():
    assert rc.validate_request({"intent": "i", "requirements": [{"id": "R-1", "text": "t"}]}) == []


def test_severity_is_fixed_by_kind():
    assert rc.severity_for("wrong") == "blocker"
    assert rc.severity_for("contradiction") == "blocker"
    assert rc.severity_for("unclear") == "major"
    assert rc.severity_for("untestable") == "major"
    for kind in ("off_icp", "missing", "unsupported_claim", "scope_creep"):
        assert rc.severity_for(kind) == "minor"


def test_normalize_drops_unknown_kinds_and_unknown_req_ids():
    req = load("request_wrong.json")
    found = rc.normalize(load("llm_blocked.json")["findings"], req, allowed_urls=set())
    kinds = [f["kind"] for f in found]
    assert "made_up_kind" not in kinds
    missing = next(f for f in found if f["kind"] == "missing")
    assert missing["req_id"] is None          # R-99 was never sent: never invent a requirement id
    wrong = next(f for f in found if f["kind"] == "wrong")
    assert wrong["req_id"] == "R-3" and wrong["severity"] == "blocker"
    assert wrong["question"] and wrong["suggested_text"]
    unclear = next(f for f in found if f["kind"] == "unclear")
    assert "suggested_text" not in unclear    # empty optionals are omitted, not sent as ""
    assert all(f["evidence"] == [] for f in found)


def test_normalize_keeps_only_evidence_from_research_sources():
    req = load("request_ok.json")
    raw = [{"req_id": "R-1", "kind": "unsupported_claim", "message": "m",
            "evidence": [{"url": "https://real.test/a", "quote": "q"},
                         {"url": "https://invented.test/b", "quote": "fabricated"}]}]
    out = rc.normalize(raw, req, allowed_urls={"https://real.test/a"})
    assert out[0]["evidence"] == [{"url": "https://real.test/a", "quote": "q"}]


def test_normalize_drops_findings_without_a_message():
    req = load("request_ok.json")
    assert rc.normalize([{"req_id": "R-1", "kind": "unclear", "message": " "}], req, set()) == []


def test_verdict_rules():
    assert rc.verdict([]) == "ok"
    assert rc.verdict([{"severity": "minor"}]) == "ok"
    assert rc.verdict([{"severity": "minor"}, {"severity": "major"}]) == "questions"
    assert rc.verdict([{"severity": "major"}, {"severity": "blocker"}]) == "blocked"


def test_merge_attaches_research_evidence_without_duplicating():
    a = [{"req_id": "R-1", "kind": "wrong", "severity": "blocker", "message": "m", "evidence": []}]
    b = [{"req_id": "R-1", "kind": "wrong", "severity": "blocker", "message": "m2",
          "evidence": [{"url": "https://s.test", "quote": "q"}]},
         {"req_id": None, "kind": "unsupported_claim", "severity": "minor", "message": "m3",
          "evidence": [{"url": "https://s.test", "quote": "q"}]}]
    out = rc.merge(a, b)
    assert len(out) == 2 and out[0]["evidence"] == [{"url": "https://s.test", "quote": "q"}]


def test_prompt_carries_intent_requirements_and_anti_overqualification_rule():
    req = load("request_wrong.json")
    prompt = rc.build_prompt(req)
    assert "freelance designers" in prompt and "R-3" in prompt
    assert "AS STATED" in prompt and "Never invent" in prompt


def test_wants_research_only_for_a_new_product():
    req = load("request_ok.json")
    assert rc.wants_research(req) is True
    assert rc.wants_research(load("request_wrong.json")) is False
    del req["context"]["existing_app"]
    assert rc.wants_research(req) is False


def test_findings_schema_lists_every_contract_kind():
    kinds = rc.findings_schema()["properties"]["findings"]["items"]["properties"]["kind"]["enum"]
    assert set(kinds) == set(rc.KINDS) and len(rc.KINDS) == 8


def test_research_query_is_short_and_omits_requirement_text():
    req = load("request_wrong.json")
    req["intent"] = "x" * 4000
    q = rc.research_query(req)
    assert len(q) < 2100 and "R-3" not in q and "freelance designers" in q
