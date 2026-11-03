from server.jobs import JobRegistry


def test_create_and_get():
    reg = JobRegistry()
    job = reg.create("sess1", "my-idea")
    assert job.state == "pending" and job.slug == "my-idea" and job.session_id == "sess1"
    assert reg.get(job.id) is job and reg.get("nope") is None


def test_lifecycle_start_record_finish():
    reg = JobRegistry()
    job = reg.create("s", "idea")
    reg.start(job.id)
    assert reg.get(job.id).state == "running"
    reg.record_stage(job.id, "frame", "GO", 4.0)
    reg.record_stage(job.id, "problem", "PIVOT", 3.0)
    reg.finish(job.id)
    j = reg.get(job.id)
    assert j.state == "done" and len(j.stages) == 2
    assert j.stages[0] == {"stage": "frame", "verdict": "GO", "score": 4.0}


def test_fail_sets_error():
    reg = JobRegistry()
    job = reg.create("s", "idea")
    reg.fail(job.id, "boom")
    j = reg.get(job.id)
    assert j.state == "error" and j.error == "boom"


def test_for_session_filters():
    reg = JobRegistry()
    a = reg.create("s1", "a"); reg.create("s2", "b"); c = reg.create("s1", "c")
    ids = {j.id for j in reg.for_session("s1")}
    assert ids == {a.id, c.id}


def test_unknown_job_ops_are_safe():
    reg = JobRegistry()
    reg.start("x"); reg.finish("x"); reg.fail("x", "e"); reg.record_stage("x", "s", "GO", 1)
    assert reg.get("x") is None
