import pytest

from pipeline.modes import MODES, guidance, resolve
from pipeline.prompts import Brief


def _brief(mode=""):
    return Brief(slug="x", title="X", body="b", meta={}, validation_mode=mode)


def test_default_is_existing_market():
    assert resolve(_brief("")).key == "existing_market"
    assert resolve(_brief("whatever")).key == "existing_market"


def test_new_market_aliases_resolve():
    for a in ("new_market", "innovation", "new market", "novel", "blue ocean", "create demand"):
        assert resolve(_brief(a)).key == "new_market", a


def test_modes_have_guidance_and_valid_demotions():
    from pipeline.gates import RULES
    for key, m in MODES.items():
        assert m.label and len(guidance(key)) > 40
        for stage, crits in m.demote_critical.items():
            assert set(crits) <= set(RULES[stage].critical), (key, stage)


def test_new_market_demotes_existing_spend_and_market_pull():
    nm = MODES["new_market"]
    assert "existing_spend" in nm.demote_critical.get("problem", ())
    assert "market_pull" in nm.demote_critical.get("market", ())


def test_guidance_unknown_empty():
    assert guidance("nope") == ""
