"""worker/req_check.py: stdin JSON in, one JSON line out, key only from the environment, no text logged."""
import io
import json

from tests.reqcheck_fixtures import load
from worker import req_check


def test_main_writes_one_result_line(monkeypatch, capsys):
    req = load("request_wrong.json")
    monkeypatch.setenv("PALGU_API_KEY", "srt_secret_value")
    seen = {}

    def fake_run(body, key, opts):
        seen["key"] = key
        return 200, {"verdict": "ok", "findings": [], "summary": "s", "model": "m",
                     "duration_ms": 1, "contract": 1}
    monkeypatch.setattr(req_check, "run_check", fake_run)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(req)))
    assert req_check.main() == 0
    out, err = capsys.readouterr()
    line = json.loads(out.strip())
    assert line["status"] == 200 and line["body"]["verdict"] == "ok"
    assert seen["key"] == "srt_secret_value"
    assert "srt_secret_value" not in out + err
    assert "Store the client's full card number" not in err   # requirement text is never logged
    assert "requirements=3" in err


def test_bad_json_on_stdin_is_422(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
    assert req_check.main() == 0
    line = json.loads(capsys.readouterr().out.strip())
    assert line["status"] == 422


def test_unexpected_crash_is_503_not_ok(monkeypatch, capsys):
    monkeypatch.setenv("PALGU_API_KEY", "k")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(load("request_ok.json"))))

    def boom(*a):
        raise RuntimeError("kaput")
    monkeypatch.setattr(req_check, "run_check", boom)
    req_check.main()
    line = json.loads(capsys.readouterr().out.strip())
    assert line["status"] == 503 and "verdict" not in line["body"]
