import json
from types import SimpleNamespace as NS

import pytest

from pipeline.config import Settings
from pipeline.gemini import GeminiClient, Research, extract_sources, parse_json


def _settings(tmp_path):
    return Settings(api_key="k", research_model="rm", structure_model="sm",
                    deep_agent="da", root=tmp_path)


def _response(text, uris=()):
    chunks = [NS(web=NS(uri=u, title=f"t-{i}")) for i, u in enumerate(uris)]
    gm = NS(grounding_chunks=chunks, web_search_queries=["q"])
    cand = NS(grounding_metadata=gm)
    return NS(text=text, candidates=[cand])


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def test_extract_sources_dedupes_and_handles_missing_metadata():
    r = _response("x", ["https://a.com/1", "https://a.com/1", "https://b.com"])
    assert [s["url"] for s in extract_sources(r)] == ["https://a.com/1", "https://b.com"]
    assert extract_sources(NS(text="x", candidates=[])) == []


def test_parse_json_strips_fences_and_raises_on_garbage():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('{"a": 1}') == {"a": 1}
    with pytest.raises(ValueError):
        parse_json("not json")


def test_research_uses_search_tool_and_returns_sources(tmp_path):
    c = GeminiClient(_settings(tmp_path))
    fake = FakeModels([_response("findings", ["https://a.com"])])
    c._models = fake
    r = c.research("prompt")
    assert isinstance(r, Research)
    assert r.text == "findings" and r.sources[0]["url"] == "https://a.com"
    assert fake.calls[0]["model"] == "rm"
    assert fake.calls[0]["config"].tools


def test_structure_requests_json_with_schema(tmp_path):
    c = GeminiClient(_settings(tmp_path))
    fake = FakeModels([_response('{"summary": "ok"}')])
    c._models = fake
    out = c.structure("text", {"type": "object", "properties": {}})
    assert out == {"summary": "ok"}
    cfg = fake.calls[0]["config"]
    assert cfg.response_mime_type == "application/json"
    assert fake.calls[0]["model"] == "sm"


def test_structure_retries_once_on_bad_json(tmp_path):
    c = GeminiClient(_settings(tmp_path))
    c._models = FakeModels([_response("garbage"), _response('{"summary": "ok"}')])
    assert c.structure("t", {"type": "object"})["summary"] == "ok"


def test_deep_research_polls_until_complete(tmp_path, monkeypatch):
    c = GeminiClient(_settings(tmp_path))
    states = [NS(status="in_progress", id="i1", outputs=None),
              NS(status="completed", id="i1",
                 outputs=[NS(text="deep text", type="text")])]

    class FakeInteractions:
        def create(self, **kw):
            return NS(id="i1", status="in_progress")

        def get(self, id):
            return states.pop(0)

    c._interactions = FakeInteractions()
    monkeypatch.setattr("pipeline.gemini.time.sleep", lambda s: None)
    r = c.deep_research("p")
    assert r.text == "deep text"
    assert r.model == "da"


def test_research_urls_uses_url_context_tool(tmp_path):
    from pipeline.config import Settings
    from pipeline.gemini import GeminiClient
    c = GeminiClient(Settings(api_key="k", research_model="rm", structure_model="sm",
                              deep_agent="da", root=tmp_path))
    from tests.test_gemini import FakeModels, _response
    fake = FakeModels([_response("site findings", ["https://typeform.com"])])
    c._models = fake
    r = c.research_urls("read https://typeform.com")
    assert r.text == "site findings"
    assert fake.calls[0]["config"].tools  # url_context (+ search) tools present
