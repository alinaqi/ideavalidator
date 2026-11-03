from pathlib import Path

from pipeline.gemini import Research
from server.jobs import JobRegistry
from server.runjob import RunSpec, run_validation

BRIEF = """---
slug: hosted-test
title: Hosted Test
date: 2026-11-03
---

# Idea brief

## One-sentence pitch
Teams can collect feedback via headless forms instead of stitching tools.
"""


class FakeClient:
    model = "fake-model"

    def research(self, prompt):
        return Research(text="research text", sources=[{"url": "https://x.test", "title": "X"}],
                        queries=["q"])

    def deep_research(self, prompt):
        return self.research(prompt)

    def research_urls(self, prompt):
        return self.research(prompt)

    def structure(self, text, schema):
        return {"summary": "s", "scores": {"a": 4, "b": 4}, "kill_flags": [], "evidence": [],
                "unknowns": []}


def _spec(tmp_path, stages="frame,problem"):
    brief = tmp_path / "hosted-test.md"
    brief.write_text(BRIEF)
    return RunSpec(brief_path=brief, out_root=tmp_path / "runs", client=FakeClient(), stages=stages)


def test_run_validation_records_stages_and_finishes(tmp_path):
    reg = JobRegistry()
    job = reg.create("sess", "hosted-test")
    run_validation(job.id, reg, _spec(tmp_path))
    j = reg.get(job.id)
    assert j.state == "done"
    assert [s["stage"] for s in j.stages] == ["frame", "problem"]
    assert all(s["verdict"] in ("GO", "PIVOT", "KILL", "UNKNOWN") for s in j.stages)
    assert (tmp_path / "runs" / "hosted-test" / "frame.json").exists()


def test_run_validation_marks_error_on_failure(tmp_path):
    reg = JobRegistry()
    job = reg.create("sess", "missing")
    spec = RunSpec(brief_path=tmp_path / "nope.md", out_root=tmp_path / "runs",
                   client=FakeClient(), stages="frame")
    run_validation(job.id, reg, spec)
    assert reg.get(job.id).state == "error" and reg.get(job.id).error
