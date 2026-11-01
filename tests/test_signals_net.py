import urllib.request

from pipeline.signals_sources import _get_json as real_get
from pipeline.signals_sources import _post_json as real_post


class _Resp:
    def __init__(self, data):
        self._d = data

    def read(self):
        return self._d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_post_json_success(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: _Resp(b'{"ok": 1}'))
    assert real_post("https://x", {}, {"a": 1}) == {"ok": 1}


def test_post_json_error_returns_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("down")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert real_post("https://x", {}, {}) is None


def test_get_json_success(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: _Resp(b"[1, 2]"))
    assert real_get("https://x", {}) == [1, 2]


def test_get_json_error_returns_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("x")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert real_get("https://x", {}) is None
