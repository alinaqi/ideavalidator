import pytest

from pipeline.evidence import normalize, score, triangulate


def test_normalize_fills_unknowns_and_uppercases():
    r = normalize({"claim": "x", "source_url": "https://a.com/p", "directness": "high"})
    assert r["directness"] == "HIGH"
    assert r["behavior_vs_stated"] == "UNKNOWN"
    assert r["recency"] == "UNKNOWN"
    assert r["independence_group"] == "a.com"
    assert r["source_type"] == "other"


def test_normalize_rejects_missing_claim():
    with pytest.raises(ValueError):
        normalize({"source_url": "https://a.com"})


def test_normalize_invalid_enum_becomes_unknown():
    r = normalize({"claim": "x", "directness": "sorta"})
    assert r["directness"] == "UNKNOWN"


def test_score_orders_behavioral_fresh_direct_highest():
    strong = normalize({"claim": "x", "directness": "HIGH",
                        "behavior_vs_stated": "BEHAVIOR", "recency": "FRESH"})
    weak = normalize({"claim": "y", "directness": "LOW",
                      "behavior_vs_stated": "STATED", "recency": "STALE"})
    unknown = normalize({"claim": "z"})
    assert score(strong) > score(unknown) > score(weak) >= 0


def test_triangulate_counts_independent_groups():
    recs = [normalize({"claim": "a", "source_url": "https://x.com/1"}),
            normalize({"claim": "b", "source_url": "https://x.com/2"}),
            normalize({"claim": "c", "source_url": "https://y.org/1"}),
            normalize({"claim": "d", "source_url": "https://z.io/1"})]
    t = triangulate(recs)
    assert t["records"] == 4
    assert t["independent_groups"] == 3
    assert t["label"] == "STRONG"
    assert triangulate(recs[:2])["label"] == "WEAK"
    assert triangulate([])["label"] == "NONE"
