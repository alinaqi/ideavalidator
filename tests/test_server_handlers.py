from pipeline.gemini import Research
from server.handlers import Deps, cancel_for, list_for, report_for, start_validation, status_for
from server.keystore import KeyStore
from server.store import RunStore
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
    keys = KeyStore()
    keys.set("sess", "srt_live")
    keys.set_account("sess", "acct1")
    return Deps(keys=keys, store=RunStore(tmp_path / "store"), root=tmp_path,
                spawn=lambda fn, *a: fn(*a), client_for=lambda key, root: FakeClient())


def test_start_validation_requires_sign_in(tmp_path):
    deps = Deps(keys=KeyStore(), store=RunStore(tmp_path), root=tmp_path)
    assert start_validation(deps, "sess", "an idea") == tools.NOT_SIGNED_IN


def test_start_runs_persists_and_reports(tmp_path):
    deps = _deps(tmp_path)
    out = start_validation(deps, "sess", "SMS waitlist for dental clinics")
    runs = deps.store.list("acct1")
    assert len(runs) == 1 and runs[0]["run_id"] in out
    rid = runs[0]["run_id"]
    status = status_for(deps, "sess", rid)
    assert status["state"] == "done" and status["completed"] == 10
    assert status["next_poll_seconds"] == 0 and status["total"] == 10
    memo = report_for(deps, "sess", rid)
    assert memo and "No such run_id" not in memo


def test_status_report_cross_session(tmp_path):
    deps = _deps(tmp_path)
    out = start_validation(deps, "sess", "an idea for devs")
    rid = deps.store.list("acct1")[0]["run_id"]
    # a NEW session/keystore, same account id, sharing the store on disk
    keys2 = KeyStore(); keys2.set("s2", "srt_live"); keys2.set_account("s2", "acct1")
    deps2 = Deps(keys=keys2, store=deps.store, root=tmp_path)
    assert status_for(deps2, "s2", rid)["run_id"] == rid
    assert "No such run_id" not in report_for(deps2, "s2", rid)
    assert rid in list_for(deps2, "s2")


def test_cancel_and_unknown(tmp_path):
    deps = _deps(tmp_path)
    start_validation(deps, "sess", "an idea")
    rid = deps.store.list("acct1")[0]["run_id"]
    assert "Cancellation requested" in cancel_for(deps, "sess", rid)
    assert "No such run_id" in cancel_for(deps, "sess", "nope")
    assert status_for(deps, "sess", "nope")["error"] == "No such run_id."
    assert list_for(deps, "sess")  # non-empty listing
