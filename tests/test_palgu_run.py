from types import SimpleNamespace

from pipeline import palgu_run


class _FakeHttp:
    def __init__(self, posts, me=None):
        self._posts = list(posts); self._me = me

    def post(self, path, body):
        return self._posts.pop(0)

    def get(self, path, key):
        return {"ok": True, "status": 200, "body": self._me}


def test_login_writes_key(tmp_path):
    posts = [
        {"ok": True, "status": 200, "body": {"device_code": "dc", "user_code": "WX-YZ",
                                             "interval": 1, "expires_in": 600}},
        {"ok": False, "status": 400, "body": {"error": "authorization_pending"}},
        {"ok": True, "status": 200, "body": {"access_token": "srt_live",
                                             "account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "free"}}},
    ]
    code = palgu_run.login(tmp_path, http=_FakeHttp(posts), sleep=lambda s: None)
    assert code == 0
    assert "PALGU_API_KEY=srt_live" in (tmp_path / ".env").read_text()


def test_login_stops_on_denied(tmp_path):
    posts = [
        {"ok": True, "status": 200, "body": {"device_code": "dc", "user_code": "WX", "interval": 1, "expires_in": 600}},
        {"ok": False, "status": 400, "body": {"error": "access_denied"}},
    ]
    assert palgu_run.login(tmp_path, http=_FakeHttp(posts), sleep=lambda s: None) == 1
    assert not (tmp_path / ".env").exists() or "PALGU_API_KEY" not in (tmp_path / ".env").read_text()


def test_login_fails_to_start(tmp_path):
    assert palgu_run.login(tmp_path, http=_FakeHttp([{"ok": False, "status": 500, "body": {}}])) == 1


def test_status_not_signed_in(tmp_path, capsys):
    palgu_run.status(tmp_path)
    assert "not signed in" in capsys.readouterr().out


def test_status_signed_in(tmp_path, capsys):
    (tmp_path / ".env").write_text("PALGU_API_KEY=srt_live\n")
    palgu_run.status(tmp_path, http=_FakeHttp([], me={"account": {"email": "a@b.com"},
                                                      "org": {"name": "Acme", "plan": "pro"}}))
    out = capsys.readouterr().out
    assert "a@b.com" in out and "Acme" in out


def test_run_palgu_cmd_dispatch(tmp_path, capsys):
    assert palgu_run.run_palgu_cmd(SimpleNamespace(action="upgrade"), tmp_path) == 0
    assert "billing" in capsys.readouterr().out
    assert palgu_run.run_palgu_cmd(SimpleNamespace(action="status"), tmp_path) == 0


def test_login_times_out(tmp_path):
    posts = [
        {"ok": True, "status": 200, "body": {"device_code": "dc", "user_code": "WX", "interval": 1, "expires_in": 2}},
        {"ok": False, "status": 400, "body": {"error": "authorization_pending"}},
        {"ok": False, "status": 400, "body": {"error": "authorization_pending"}},
    ]
    assert palgu_run.login(tmp_path, http=_FakeHttp(posts), sleep=lambda s: None) == 1
