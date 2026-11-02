from types import SimpleNamespace

from pipeline.palgu_client import PalguClient, _extract_json


def _settings():
    return SimpleNamespace(api_key="srt_k", research_model="gemini-3.8-flash",
                           structure_model="gemini-3.8-flash", palgu_base="https://api.palgu.ai/v1")


def test_extract_json_plain_and_fenced():
    assert _extract_json('{"a": 1}') == {"a": 1}
    assert _extract_json('noise ```json\n{"b": 2}\n``` tail') == {"b": 2}
    assert _extract_json("not json at all") == {}


def test_research_calls_grounded_endpoint_and_maps_sources():
    captured = {}
    def post(url, headers, body):
        captured["url"] = url; captured["headers"] = headers; captured["body"] = body
        return {"text": "grounded answer", "searched": True, "model": "gemini-3.8-flash",
                "queries": ["q1", "q2"],
                "sources": [{"url": "https://a.test", "title": "A"},
                            {"url": "https://b.test"}, "https://c.test"]}
    c = PalguClient(_settings(), post=post)
    r = c.research("find evidence")
    assert r.text == "grounded answer" and r.model == "gemini-3.8-flash"
    assert captured["url"].endswith("/v1/research")
    assert captured["body"] == {"query": "find evidence"}
    assert captured["headers"]["Authorization"] == "Bearer srt_k"
    assert captured["headers"].get("Idempotency-Key")
    assert r.queries == ["q1", "q2"]
    assert r.sources[0] == {"url": "https://a.test", "title": "A"}
    assert r.sources[1] == {"url": "https://b.test", "title": ""}
    assert r.sources[2] == {"url": "https://c.test", "title": ""}


def test_structure_returns_parsed_json():
    def post(url, headers, body):
        return {"choices": [{"message": {"content": '{"summary": "s", "scores": {"a": 4}}'}}]}
    c = PalguClient(_settings(), post=post)
    out = c.structure("research text with sources", {"type": "object"})
    assert out["summary"] == "s" and out["scores"]["a"] == 4


def test_research_maps_model_dict_to_alias_string():
    def post(url, headers, body):
        return {"text": "t", "sources": [], "queries": [],
                "model": {"alias": "gemini-3.7-flash", "model_id": "gemini-3.7-flash"}}
    r = PalguClient(_settings(), post=post).research("x")
    assert r.model == "gemini-3.7-flash"


def test_research_degrades_on_empty_response():
    c = PalguClient(_settings(), post=lambda u, h, b: None)
    r = c.research("x")
    assert r.text == "" and r.sources == [] and r.queries == []


def test_deep_and_urls_aliases_work():
    c = PalguClient(_settings(), post=lambda u, h, b: {"text": "t", "sources": [], "queries": []})
    assert c.deep_research("x").text == "t" and c.research_urls("x").text == "t"
