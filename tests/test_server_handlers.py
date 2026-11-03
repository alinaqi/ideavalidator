from pipeline.gemini import Research
from server.handlers import Deps, report_for, start_validation
from server.jobs import JobRegistry
from server.keystore import KeyStore
from server import tools


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


def _deps(tmp_path):
    return Deps(keys=KeyStore(), jobs=JobRegistry(), store=tmp_path, root=tmp_path,
                spawn=lambda fn, *a: fn(*a), client_for=lambda key, root: FakeClient())


def test_start_validation_requires_sign_in(tmp_path):
    deps = _deps(tmp_path)
    assert start_validation(deps, "sess", "an idea") == tools.NOT_SIGNED_IN


def test_start_validation_runs_and_reports(tmp_path):
    deps = _deps(tmp_path)
    deps.keys.set("sess", "srt_live")
    out = start_validation(deps, "sess", "SMS waitlist for dental clinics")
    jobs = deps.jobs.for_session("sess")
    assert len(jobs) == 1 and jobs[0].id in out
    assert jobs[0].state == "done" and len(jobs[0].stages) == 10
    memo = report_for(deps, "sess", jobs[0].id)
    assert memo and "No such run_id" not in memo


def test_report_for_unknown_run(tmp_path):
    assert "No such run_id" in report_for(_deps(tmp_path), "sess", "nope")
