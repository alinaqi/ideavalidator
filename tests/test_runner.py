import json

import pytest

from pipeline.prompts import load_brief
from pipeline.runner import (MissingDependency, RunContext, load_output,
                             prior_summaries, run_stage)
from pipeline.stages import get_stage
from tests.conftest import FakeClient


def _ctx(brief_path, out_dir, client=None, deep=False):
    return RunContext(brief=load_brief(brief_path), out_dir=out_dir,
                      client=client or FakeClient(), deep=deep)


def test_run_stage_writes_json_and_md(brief_path, out_dir):
    ctx = _ctx(brief_path, out_dir)
    data = run_stage(get_stage("frame"), ctx)
    assert (out_dir / "frame.json").exists()
    assert (out_dir / "frame.md").exists()
    assert data["stage"] == "frame"
    assert data["idea"] == "test-idea"
    assert data["model"] == "fake-model"
    assert data["generated_at"]
    assert data["sources"][0]["url"] == "https://src.example/1"
    assert data["gate"]["verdict"] in {"GO", "PIVOT", "KILL", "UNKNOWN"}


def test_run_stage_requires_dependencies(brief_path, out_dir):
    with pytest.raises(MissingDependency):
        run_stage(get_stage("problem"), _ctx(brief_path, out_dir))


def test_run_stage_feeds_prior_summaries_into_prompt(brief_path, seeded_out_dir):
    client = FakeClient()
    run_stage(get_stage("market"), _ctx(brief_path, seeded_out_dir, client))
    assert "summary for frame" in client.prompts[0]
    assert "summary for problem" in client.prompts[0]


def test_run_stage_deep_mode_uses_deep_research(brief_path, out_dir):
    client = FakeClient()
    run_stage(get_stage("frame"), _ctx(brief_path, out_dir, client, deep=True))
    assert client.prompts[0].startswith("DEEP:")


def test_run_stage_normalizes_evidence_and_adds_triangulation(brief_path, out_dir):
    client = FakeClient({"summary": "s", "scores": {}, "kill_flags": [],
                         "evidence": [{"claim": "c", "source_url": "https://a.com/x"}],
                         "unknowns": []})
    data = run_stage(get_stage("frame"), _ctx(brief_path, out_dir, client))
    assert data["evidence"][0]["directness"] == "UNKNOWN"
    assert data["triangulation"]["records"] == 1


def test_load_output_and_prior_summaries(seeded_out_dir):
    assert load_output(seeded_out_dir, "frame")["stage"] == "frame"
    assert load_output(seeded_out_dir, "market") is None
    ps = prior_summaries(seeded_out_dir, ("frame", "problem"))
    assert ps == {"frame": "summary for frame", "problem": "summary for problem"}


def test_decision_prompt_includes_council_summary_when_present(brief_path, out_dir):
    from pipeline.stages import STAGES

    for s in STAGES[:-1]:
        (out_dir / f"{s.id}.json").write_text(json.dumps({"stage": s.id, "summary": f"sum {s.id}"}))
    (out_dir / "council.json").write_text(json.dumps({"summary": "COUNCIL SAID X"}))
    client = FakeClient()
    run_stage(get_stage("decision"), _ctx(brief_path, out_dir, client))
    assert "COUNCIL SAID X" in client.prompts[0]
