import json

from pipeline.report import build_memo, render_stage
from tests.conftest import stage_output


def test_render_stage_contains_core_sections():
    data = stage_output("problem", {"problem_evidence": 4})
    data["gate"] = {"verdict": "GO", "score": 4.0, "reasons": ["ok"]}
    data["sources"] = [{"url": "https://example.com/a", "title": "A"}]
    data["verticals"] = [{"name": "Dental", "score": 4}]
    md = render_stage(data)
    assert md.startswith("# ")
    assert "GO" in md and "summary for problem" in md
    assert "example.com/a" in md
    assert "Dental" in md
    assert "Actual budget authority" in md


def test_build_memo_rolls_up_gates(seeded_out_dir):
    for sid in ("frame", "problem"):
        p = seeded_out_dir / f"{sid}.json"
        d = json.loads(p.read_text())
        d["gate"] = {"verdict": "GO" if sid == "frame" else "PIVOT",
                     "score": 3.0, "reasons": ["r"]}
        p.write_text(json.dumps(d))
    memo = build_memo(seeded_out_dir)
    assert "PIVOT" in memo
    assert "frame" in memo and "problem" in memo
    assert "not yet run" in memo.lower()


def test_build_memo_empty_dir(out_dir):
    memo = build_memo(out_dir)
    assert "UNKNOWN" in memo


def _seed_gates(out_dir):
    for sid in ("frame", "problem"):
        p = out_dir / f"{sid}.json"
        d = json.loads(p.read_text())
        d["gate"] = {"verdict": "GO", "score": 4.0, "reasons": ["r"]}
        p.write_text(json.dumps(d))


def test_build_memo_includes_demand_signals_when_present(seeded_out_dir):
    _seed_gates(seeded_out_dir)
    (seeded_out_dir / "signals.json").write_text(json.dumps({
        "query": "survey creator", "bonus": 0.35, "score": 0.7,
        "search": [{"source": "dataforseo", "kind": "search_volume",
                    "label": "survey creator", "value": 5400, "detail": "", "url": ""}],
        "social": [{"source": "apify", "kind": "social", "label": "best survey tool?",
                    "value": 14, "detail": "", "url": "https://reddit.com/x"}]}))
    memo = build_memo(seeded_out_dir)
    assert "Demand signals" in memo and "survey creator" in memo and "+0.35" in memo


def test_build_memo_no_signals_section_when_absent(seeded_out_dir):
    _seed_gates(seeded_out_dir)
    assert "Demand signals" not in build_memo(seeded_out_dir)
