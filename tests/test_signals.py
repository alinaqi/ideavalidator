import pytest

from pipeline.prompts import Brief
from pipeline.signals import (
    DemandSignals, Signal, compute_bonus, from_dict, gather, keywords_for,
    summarize, to_dict,
)


def _brief():
    return Brief(slug="typeform-survey", title="Typeform — free survey creator",
                 body="## Candidate verticals\n- ecommerce\n- SaaS\n", meta={})


class FakeFetchers:
    def __init__(self, search=None, social=None, boom=False):
        self._search, self._social, self._boom = search or [], social or [], boom

    def search_volume(self, keywords, keys):
        if self._boom:
            raise RuntimeError("api down")
        return self._search

    def social(self, query, keys):
        if self._boom:
            raise RuntimeError("api down")
        return self._social


def test_keywords_include_title_terms():
    kws = keywords_for(_brief())
    assert kws and any("survey" in k.lower() for k in kws)
    assert len(kws) <= 5


def test_compute_bonus_strong_signals_capped_at_half():
    search = [Signal("dataforseo", "search_volume", "survey creator", 5000, "", "")]
    social = [Signal("apify", "social", f"thread {i}", None, "u", "") for i in range(12)]
    score, bonus = compute_bonus(search, social)
    assert bonus == 0.5 and score == 1.0


def test_compute_bonus_none_is_zero_no_penalty():
    score, bonus = compute_bonus([], [])
    assert bonus == 0.0 and score == 0.0


def test_compute_bonus_mid_is_between():
    search = [Signal("dataforseo", "search_volume", "k", 200, "", "")]
    social = [Signal("apify", "social", "t", None, "u", "")]
    score, bonus = compute_bonus(search, social)
    assert 0.0 < bonus < 0.5


def test_gather_builds_signals_and_bonus():
    search = [Signal("dataforseo", "search_volume", "survey creator", 5000, "", "")]
    social = [Signal("grok", "social", "x chatter", 8, "u", "")]
    ds = gather(_brief(), {}, FakeFetchers(search, social))
    assert isinstance(ds, DemandSignals)
    assert ds.search and ds.social and ds.bonus > 0


def test_gather_degrades_when_sources_fail():
    ds = gather(_brief(), {}, FakeFetchers(boom=True))
    assert ds.search == [] and ds.social == [] and ds.bonus == 0.0


def test_summarize_mentions_volume():
    ds = gather(_brief(), {}, FakeFetchers(
        [Signal("dataforseo", "search_volume", "survey creator", 5000, "", "")], []))
    assert "5000" in summarize(ds) and "survey creator" in summarize(ds)


def test_to_dict_roundtrip():
    ds = gather(_brief(), {}, FakeFetchers(
        [Signal("dataforseo", "search_volume", "k", 10, "d", "u")],
        [Signal("apify", "social", "t", 3, "x", "u")]))
    again = from_dict(to_dict(ds))
    assert again.bonus == ds.bonus and again.search[0].value == 10
