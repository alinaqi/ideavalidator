from server import tools
from server.jobs import JobRegistry


def test_not_signed_in_constant_mentions_login():
    assert "palgu_login" in tools.NOT_SIGNED_IN


def test_started_text_has_run_id():
    reg = JobRegistry(); job = reg.create("s", "idea")
    txt = tools.started_text(job)
    assert job.id in txt and "get_status" in txt


def test_progress_text_states():
    reg = JobRegistry(); job = reg.create("s", "idea")
    assert "No such run_id" in tools.progress_text(None)
    reg.start(job.id); reg.record_stage(job.id, "frame", "GO", 4.0)
    out = tools.progress_text(reg.get(job.id))
    assert "running" in out and "frame" in out and "GO" in out
    reg.fail(job.id, "boom")
    assert "boom" in tools.progress_text(reg.get(job.id))


def test_report_text_branches(tmp_path):
    reg = JobRegistry(); job = reg.create("s", "idea")
    assert "No such run_id" in tools.report_text(tmp_path, tmp_path, None)
    assert "once state is 'done'" in tools.report_text(tmp_path, tmp_path, reg.get(job.id))
    reg.finish(job.id)
    (tmp_path / "decision.md").write_text("# Decision\nGO")
    assert "GO" in tools.report_text(tmp_path, tmp_path, reg.get(job.id))
