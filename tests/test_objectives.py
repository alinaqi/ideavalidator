import pytest

from pipeline.objectives import OBJECTIVES, guidance, resolve
from pipeline.prompts import Brief


def _brief(success=""):
    return Brief(slug="x", title="X", body="b", meta={}, business_model="", success_definition=success)


def test_default_when_blank_or_unknown():
    assert resolve(_brief("")).key == "default"
    assert resolve(_brief("nonsense")).key == "default"


def test_known_objectives_resolve_by_token_or_alias():
    assert resolve(_brief("compounding_product")).key == "compounding_product"
    assert resolve(_brief("PLG / network")).key == "plg_network"
    assert resolve(_brief("services / cash now")).key == "services_cash"
    assert resolve(_brief("venture")).key == "venture_scale"


def test_every_objective_has_guidance_and_valid_demotions():
    from pipeline.gates import RULES

    for key, obj in OBJECTIVES.items():
        assert obj.label and len(guidance(key)) > 40
        for stage, crits in obj.demote_critical.items():
            assert stage in RULES
            assert set(crits) <= set(RULES[stage].critical), (key, stage)


def test_compounding_and_plg_demote_immediate_wtp_criticals():
    plg = OBJECTIVES["plg_network"]
    assert "behavioral_signal" in plg.demote_critical.get("wtp", ()) or \
           "budget_exists" in plg.demote_critical.get("wtp", ())
    assert "breakeven_reachability" in OBJECTIVES["compounding_product"].demote_critical.get("economics", ())


def test_guidance_unknown_key_is_empty():
    assert guidance("nope") == ""
