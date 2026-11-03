from server import tools


def _meta(state="running", stages=None):
    return {"run_id": "abc123", "slug": "an-idea", "state": state,
            "stages": stages or [], "cancel": False, "created": 0}


def test_not_signed_in_mentions_login():
    assert "palgu_login" in tools.NOT_SIGNED_IN


def test_next_poll_seconds():
    assert tools.next_poll_seconds("running") == 120
    assert tools.next_poll_seconds("pending") == 20
    assert tools.next_poll_seconds("done") == 0


def test_started_text_has_run_id():
    txt = tools.started_text(_meta())
    assert "abc123" in txt and "get_status" in txt


def test_progress_payload():
    assert tools.progress_payload(None)["error"] == "No such run_id."
    p = tools.progress_payload(_meta("running", [{"stage": "frame", "verdict": "GO", "score": 4.0}]))
    assert p["state"] == "running" and p["completed"] == 1 and p["total"] == tools.TOTAL
    assert p["next_poll_seconds"] == 120 and p["stages"][0]["stage"] == "frame"


def test_list_text():
    assert tools.list_text([]) == "No runs yet."
    out = tools.list_text([_meta("done", [1] * 10), _meta("running")])
    assert "abc123" in out and "done" in out and "running" in out


def test_report_text_branches(tmp_path):
    assert "No such run_id" in tools.report_text(tmp_path, tmp_path, None)
    assert "once state is 'done'" in tools.report_text(tmp_path, tmp_path, _meta("running"))
    (tmp_path / "an-idea").mkdir()
    (tmp_path / "an-idea" / "decision.md").write_text("# Decision\nGO")
    assert "GO" in tools.report_text(tmp_path, tmp_path, _meta("done"))
