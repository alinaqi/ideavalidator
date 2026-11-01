import urllib.error
import urllib.request

from pipeline.selfcheck_run import reachable as real_reachable


class _CM:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code):
    def boom(*a, **k):
        raise urllib.error.HTTPError("u", code, "err", {}, None)
    return boom


def test_reachable_true_on_success(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: _CM())
    assert real_reachable("https://ok.example") is True


def test_reachable_false_on_404(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _http_error(404))
    assert real_reachable("https://dead.example") is False


def test_reachable_true_on_500_ambiguous(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _http_error(500))
    assert real_reachable("https://flaky.example") is True


def test_reachable_true_on_network_error(monkeypatch):
    def boom(*a, **k):
        raise urllib.error.URLError("down")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert real_reachable("https://nohost.example") is True
