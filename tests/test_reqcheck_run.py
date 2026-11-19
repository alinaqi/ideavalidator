"""run_check end to end with an injected Palgu `post`: every verdict and every error path of contract v1."""
import json

import pytest

from pipeline import reqcheck_run as run
from tests.reqcheck_fixtures import load

KEY = "srt_test_key_never_logged"


def _chat_reply(payload, model="gemini-3.8-flash"):
    return {"model": model, "choices": [{"message": {"content": json.dumps(payload)}}]}


def _poster(chat_payload, research=None, fail=None):
    calls = []

    def post(url, headers, body, timeout):
        calls.append({"url": url, "headers": headers, "body": body, "timeout": timeout})
        if fail:
            raise fail
        if url.endswith("/research"):
            return research or {"text": "", "sources": []}
        return _chat_reply(chat_payload)
    return post, calls


def _check(req, post):
    return run.run_check(req, KEY, run.Options(post=post, base="https://palgu.test/v1",
                                                 model="gemini-3.8-flash"))


@pytest.mark.parametrize("llm,verdict", [("llm_blocked.json", "blocked"),
                                         ("llm_questions.json", "questions"),
                                         ("llm_ok.json", "ok")])
def test_each_verdict(llm, verdict):
    post, calls = _poster(load(llm))
    status, body = _check(load("request_wrong.json"), post)
    assert status == 200 and body["verdict"] == verdict
    assert body["contract"] == 1 and body["model"] == "gemini-3.8-flash"
    assert isinstance(body["duration_ms"], int) and body["summary"]
    assert len(calls) == 1                       # existing app: one structured call, no research
    chat = calls[0]
    assert chat["headers"]["Authorization"] == f"Bearer {KEY}"
    assert chat["body"]["response_format"]["type"] == "json_schema"


def test_new_product_adds_grounded_research_with_real_citations():
    research = {"text": "Common CLI tools count words as whitespace-separated tokens.",
                "sources": [{"url": "https://man.test/wc", "title": "wc"}]}
    evidence_pass = {"summary": "", "findings": [
        {"req_id": "R-1", "kind": "unsupported_claim", "message": "m",
         "evidence": [{"url": "https://man.test/wc", "quote": "counts words"},
                      {"url": "https://fake.test", "quote": "x"}]}]}
    calls = []

    def post(url, headers, body, timeout):
        calls.append(url)
        if url.endswith("/research"):
            return research
        prompt = body["messages"][-1]["content"]
        return _chat_reply(evidence_pass if "Research notes" in prompt else load("llm_ok.json"))
    status, body = _check(load("request_ok.json"), post)
    assert status == 200 and body["verdict"] == "ok"
    assert sum(u.endswith("/research") for u in calls) == 1
    ev = body["findings"][0]["evidence"]
    assert ev == [{"url": "https://man.test/wc", "quote": "counts words"}]


def test_research_failure_still_returns_the_main_check():
    def post(url, headers, body, timeout):
        if url.endswith("/research"):
            raise run.CheckFailed(503, "palgu_unavailable", "research down")
        return _chat_reply(load("llm_questions.json"))
    status, body = _check(load("request_ok.json"), post)
    assert status == 200 and body["verdict"] == "questions"
    assert "research skipped" in body["summary"]


@pytest.mark.parametrize("status,code", [(401, "unauthorized"), (402, "payment_required"),
                                         (503, "palgu_unavailable")])
def test_palgu_errors_map_to_contract_status(status, code):
    post, _ = _poster({}, fail=run.CheckFailed(status, code, "x"))
    got, body = _check(load("request_wrong.json"), post)
    assert got == status and body["error"]["code"] == code
    assert "verdict" not in body


def test_402_body_is_passed_through():
    upstream = {"error": {"code": "budget_exceeded", "message": "top up"}}
    post, _ = _poster({}, fail=run.CheckFailed(402, "payment_required", "x", upstream))
    got, body = _check(load("request_wrong.json"), post)
    assert got == 402 and body == upstream


def test_unparseable_model_output_is_503_never_ok():
    def post(url, headers, body, timeout):
        return {"choices": [{"message": {"content": "sorry, I cannot"}}]}
    got, body = _check(load("request_wrong.json"), post)
    assert got == 503 and body["error"]["code"] == "check_failed"


def test_invalid_body_is_422():
    got, body = _check({"intent": ""}, _poster({})[0])
    assert got == 422 and body["error"]["code"] == "invalid_body"


def test_missing_key_is_401():
    got, _ = run.run_check(load("request_ok.json"), "", run.Options(post=_poster({})[0]))
    assert got == 401


def test_http_status_classification():
    assert run.classify_status(401) == (401, "unauthorized")
    assert run.classify_status(403) == (401, "unauthorized")
    assert run.classify_status(402) == (402, "payment_required")
    assert run.classify_status(500) == (503, "palgu_unavailable")
    assert run.classify_status(429) == (503, "palgu_unavailable")


def _http_error(code, body):
    import io
    import urllib.error
    return urllib.error.HTTPError("https://palgu.test", code, "x", {}, io.BytesIO(body))


def test_post_json_maps_http_errors_and_keeps_the_402_body(monkeypatch):
    def raise_402(req, timeout):
        raise _http_error(402, b'{"error": {"code": "budget_exceeded"}}')
    monkeypatch.setattr(run.urllib.request, "urlopen", raise_402)
    with pytest.raises(run.CheckFailed) as exc:
        run.post_json("https://palgu.test/v1/chat/completions", {}, {}, 5)
    assert exc.value.status == 402 and exc.value.body == {"error": {"code": "budget_exceeded"}}


def test_post_json_network_failure_is_503(monkeypatch):
    def boom(req, timeout):
        raise TimeoutError()
    monkeypatch.setattr(run.urllib.request, "urlopen", boom)
    with pytest.raises(run.CheckFailed) as exc:
        run.post_json("https://palgu.test/v1/research", {}, {}, 5)
    assert exc.value.status == 503 and exc.value.message == "TimeoutError"


def test_post_json_returns_parsed_body(monkeypatch):
    import io

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(run.urllib.request, "urlopen", lambda req, timeout: Resp(b'{"a": 1}'))
    assert run.post_json("https://palgu.test/v1/x", {}, {}, 5) == {"a": 1}


def test_research_without_sources_adds_nothing():
    def post(url, headers, body, timeout):
        if url.endswith("/research"):
            return {"text": "no sources", "sources": []}
        return _chat_reply(load("llm_ok.json"))
    status, body = _check(load("request_ok.json"), post)
    assert status == 200 and body["findings"] == [] and "research skipped" not in body["summary"]
