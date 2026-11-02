import urllib.error
import urllib.request

from pipeline.palgu_client import _post_json as real_post
from pipeline.palgu_run import _Http


class _Resp:
    def __init__(self, data, status=200):
        self._d = data; self.status = status

    def read(self):
        return self._d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_http_send_success(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: _Resp(b'{"x": 1}', 200))
    out = _Http().post("/auth/device/code", {"a": 1})
    assert out["ok"] is True and out["body"] == {"x": 1}


def test_http_send_httperror_with_body(monkeypatch):
    def boom(*a, **k):
        err = urllib.error.HTTPError("u", 400, "bad", {}, None)
        err.read = lambda: b'{"error": "authorization_pending"}'
        raise err
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    out = _Http().post("/auth/token", {})
    assert out["ok"] is False and out["status"] == 400 and out["body"]["error"] == "authorization_pending"


def test_palgu_client_post_json_success(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: _Resp(b'{"ok": 1}'))
    assert real_post("https://api.palgu.ai/v1/chat/completions", {}, {"m": 1}) == {"ok": 1}


def test_palgu_client_post_json_error_returns_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("down")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert real_post("https://api.palgu.ai/v1/chat/completions", {}, {}) is None


def test_palgu_client_post_json_402_warns_and_returns_none(monkeypatch, capsys):
    def boom(*a, **k):
        raise urllib.error.HTTPError("u", 402, "payment required", {}, None)
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert real_post("https://api.palgu.ai/v1/research", {}, {"query": "x"}) is None
    err = capsys.readouterr().err
    assert "402" in err and "budget" in err.lower() and "palgu.ai/billing" in err
