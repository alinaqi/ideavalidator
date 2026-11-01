import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BRIEF = """---
slug: test-idea
title: Test Idea
date: 2026-10-31
---

# Idea brief

## One-sentence pitch
Dentists struggling with no-shows can fill slots using SMS waitlists.
"""


@pytest.fixture
def brief_path(tmp_path):
    p = tmp_path / "test-idea.md"
    p.write_text(BRIEF)
    return p


@pytest.fixture
def out_dir(tmp_path):
    d = tmp_path / "runs" / "test-idea"
    d.mkdir(parents=True)
    return d


def stage_output(stage_id, scores, flags=()):
    return {
        "stage": stage_id,
        "summary": f"summary for {stage_id}",
        "scores": scores,
        "kill_flags": list(flags),
        "evidence": [
            {
                "claim": "Dentists report 10-20% no-show rates",
                "source_url": "https://example.com/a",
                "source_type": "report",
                "directness": "HIGH",
                "behavior_vs_stated": "BEHAVIOR",
                "recency": "FRESH",
                "independence_group": "example.com",
            }
        ],
        "unknowns": ["Actual budget authority of office manager"],
    }


@pytest.fixture
def seeded_out_dir(out_dir):
    for sid in ("frame", "problem"):
        (out_dir / f"{sid}.json").write_text(
            json.dumps(stage_output(sid, {"a": 4, "b": 4}))
        )
    return out_dir


class FakeClient:
    """Stands in for GeminiClient: records prompts, returns canned JSON."""

    def __init__(self, structured=None):
        self.prompts = []
        self.structured = structured or {
            "summary": "canned summary",
            "scores": {"problem_evidence": 4, "urgency": 3},
            "kill_flags": [],
            "evidence": [],
            "unknowns": [],
        }
        self.model = "fake-model"

    def research(self, prompt):
        self.prompts.append(prompt)
        from pipeline.gemini import Research

        return Research(text="research text", sources=[
            {"url": "https://src.example/1", "title": "Src 1"}
        ], queries=["q1"])

    def deep_research(self, prompt):
        return self.research("DEEP:" + prompt)

    def research_urls(self, prompt):
        self.prompts.append(prompt)
        from pipeline.gemini import Research

        return Research(text="research text from site", sources=[
            {"url": "https://zenloop.com", "title": "Zenloop"}
        ], queries=["zenloop"])

    def structure(self, text, schema):
        assert "research text" in text
        assert isinstance(schema, dict)
        return dict(self.structured)


@pytest.fixture(autouse=True)
def _block_signal_network(monkeypatch):
    """No test may make a real demand-signal API call; individual tests stub responses explicitly."""
    from pipeline import signals_sources
    monkeypatch.setattr(signals_sources, "_post_json", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(signals_sources, "_get_json", lambda *a, **k: None, raising=False)
