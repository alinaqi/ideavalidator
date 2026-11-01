import urllib.request

from pipeline.reddit_source import _search_json as real_search
from pipeline.reddit_source import _token as real_token


class _Resp:
    def __init__(self, d):
        self._d = d

    def read(self):
        return self._d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_token_success(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=0: _Resp(b'{"access_token": "tok"}'))
    assert real_token({"REDDIT_CLIENT_ID": "c", "REDDIT_CLIENT_SECRET": "s"}) == "tok"


def test_token_none_without_creds():
    assert real_token({}) is None


def test_token_error_returns_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("x")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert real_token({"REDDIT_CLIENT_ID": "c", "REDDIT_CLIENT_SECRET": "s"}) is None


def test_search_json_success(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=0: _Resp(b'{"data": {"children": []}}'))
    assert real_search("tok", "q", "ua") == {"data": {"children": []}}


def test_search_json_error_returns_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("x")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert real_search("tok", "q", "ua") is None
