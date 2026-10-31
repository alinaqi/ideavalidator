import pytest

from pipeline.stages import STAGES, get_stage, resolve, stage_ids

EXPECTED = ["frame", "problem", "market", "icp", "swot",
            "wtp", "economics", "risks", "decision"]


def test_canonical_order():
    assert stage_ids() == EXPECTED


def test_every_stage_has_pdlc_state_and_question():
    for s in STAGES:
        assert s.pdlc_state.startswith("S")
        assert s.question.endswith("?")


def test_dependencies_point_backwards_only():
    seen = set()
    for s in STAGES:
        assert set(s.depends_on) <= seen, s.id
        seen.add(s.id)


def test_decision_depends_on_everything_before_it():
    assert set(get_stage("decision").depends_on) == set(EXPECTED[:-1])


def test_resolve_all_and_subset_keeps_canonical_order():
    assert [s.id for s in resolve("all")] == EXPECTED
    assert [s.id for s in resolve("wtp,frame")] == ["frame", "wtp"]


def test_resolve_unknown_raises():
    with pytest.raises(ValueError):
        resolve("frame,bogus")
    with pytest.raises(KeyError):
        get_stage("bogus")


def test_decision_optionally_consumes_council():
    assert "council" in get_stage("decision").optional
    assert all(not set(s.optional) & set(s.depends_on) for s in STAGES)
