from pipeline.gemini import Research
from server.runjob import RunSpec, run_validation
from server.store import RunStore

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


def _spec(store, ref, tmp_path, stages="frame,problem"):
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF)
    return RunSpec(brief_path=brief, out_root=store.path(ref), client=FakeClient(), stages=stages)


def test_run_validation_records_stages_and_finishes(tmp_path):
    s = RunStore(tmp_path / "store")
    ref, _ = s.create("acct", "hosted-test")
    run_validation(s, ref, _spec(s, ref, tmp_path))
    m = s.get(ref)
    assert m["state"] == "done"
    assert [x["stage"] for x in m["stages"]] == ["frame", "problem"]
    assert (s.path(ref) / "hosted-test" / "frame.json").exists()


def test_run_validation_marks_error(tmp_path):
    s = RunStore(tmp_path / "store")
    ref, _ = s.create("acct", "missing")
    spec = RunSpec(brief_path=tmp_path / "nope.md", out_root=s.path(ref),
                   client=FakeClient(), stages="frame")
    run_validation(s, ref, spec)
    assert s.get(ref)["state"] == "error" and s.get(ref)["error"]


def test_run_validation_honours_cancel(tmp_path):
    s = RunStore(tmp_path / "store")
    ref, _ = s.create("acct", "hosted-test")
    s.update(ref, {"cancel": True})
    run_validation(s, ref, _spec(s, ref, tmp_path))
    m = s.get(ref)
    assert m["state"] == "cancelled" and m["stages"] == []
