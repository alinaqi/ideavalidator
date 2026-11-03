from server.store import RunRef, RunStore, account_id


def test_account_id_stable_short_distinct():
    a = account_id("a@b.com")
    assert len(a) == 16 and a == account_id("a@b.com")
    assert a != account_id("c@d.com")
    assert account_id("") == account_id(None)  # anon fallback is stable


def test_create_get_list(tmp_path):
    s = RunStore(tmp_path)
    ref, meta = s.create("acct1", "idea-a")
    assert meta["state"] == "pending" and meta["slug"] == "idea-a" and ref.run_id
    assert s.get(ref)["run_id"] == ref.run_id
    s.create("acct1", "idea-b")
    assert len(s.list("acct1")) == 2
    assert s.list("other") == []
    assert s.get(RunRef("acct1", "nope")) is None


def test_update_record_stage_and_guards(tmp_path):
    s = RunStore(tmp_path)
    ref, _ = s.create("acct", "idea")
    s.update(ref, {"state": "running"})
    assert s.get(ref)["state"] == "running"
    s.record_stage(ref, {"stage": "frame", "verdict": "GO", "score": 4.0})
    s.record_stage(ref, {"stage": "problem", "verdict": "KILL", "score": 1.0})
    assert [x["stage"] for x in s.get(ref)["stages"]] == ["frame", "problem"]
    assert s.update(RunRef("acct", "nope"), {"x": 1}) is None
    s.record_stage(RunRef("acct", "nope"), {"stage": "x"})  # no-op, no crash


def test_persists_across_instances(tmp_path):
    ref, _ = RunStore(tmp_path).create("acct", "idea")
    assert RunStore(tmp_path).get(ref)["slug"] == "idea"
    assert RunStore(tmp_path).list("acct")[0]["run_id"] == ref.run_id
