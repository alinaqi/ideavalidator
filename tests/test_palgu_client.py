from types import SimpleNamespace

from pipeline.palgu_client import PalguClient, _extract_json


def _settings():
    return SimpleNamespace(api_key="srt_k", research_model="gemini-3.8-flash",
                           structure_model="gemini-3.8-flash", palgu_base="https://api.palgu.ai/v1")


def test_extract_json_plain_and_fenced():
    assert _extract_json('{"a": 1}') == {"a": 1}
    assert _extract_json('noise ```json\n{"b": 2}\n``` tail') == {"b": 2}
    assert _extract_json("not json at all") == {}


def test_research_calls_chat_completions_with_pin():
    captured = {}
    def post(url, headers, body):
        captured["url"] = url; captured["headers"] = headers; captured["body"] = body
        return {"choices": [{"message": {"content": "research text"}}]}
    c = PalguClient(_settings(), post=post)
    r = c.research("find evidence")
    assert r.text == "research text" and r.model == "gemini-3.8-flash"
    assert captured["url"].endswith("/v1/chat/completions")
    assert captured["headers"]["x-srooter-pin"] == "gemini-3.8-flash"
    assert captured["headers"]["Authorization"] == "Bearer srt_k"
    assert captured["body"]["messages"][0]["content"] == "find evidence"


def test_structure_returns_parsed_json():
    def post(url, headers, body):
        return {"choices": [{"message": {"content": '{"summary": "s", "scores": {"a": 4}}'}}]}
    c = PalguClient(_settings(), post=post)
    out = c.structure("research text with sources", {"type": "object"})
    assert out["summary"] == "s" and out["scores"]["a"] == 4


def test_research_degrades_on_empty_response():
    c = PalguClient(_settings(), post=lambda u, h, b: None)
    assert c.research("x").text == ""


def test_deep_and_urls_aliases_work():
    c = PalguClient(_settings(), post=lambda u, h, b: {"choices": [{"message": {"content": "t"}}]})
    assert c.deep_research("x").text == "t" and c.research_urls("x").text == "t"
