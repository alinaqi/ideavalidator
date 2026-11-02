"""A drop-in replacement for GeminiClient that runs the pipeline on Palgu's single-key gateway, so a
signed-in user needs no GEMINI_API_KEY. research/deep_research/research_urls call Palgu's grounded
`/v1/research` endpoint (real citations via Google Search, srooter#2063); structure uses OpenAI-compatible
`/v1/chat/completions` with a json_schema response_format, pinned with the `x-srooter-pin` header. Network
is injected (`post`) for testing; it is best-effort and returns "" / [] / {} on any failure.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request

from .gemini import Research
from .palgu import PALGU_V1


def _post_json(url: str, headers: dict, body: dict) -> object:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _map_sources(items: object) -> list:
    out = []
    for item in items or []:
        if isinstance(item, dict):
            out.append({"url": item.get("url", ""), "title": item.get("title", "")})
        elif isinstance(item, str):
            out.append({"url": item, "title": ""})
    return out


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text or "", re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group())
        except Exception:
            return {}


class PalguClient:
    """Pipeline client backed by Palgu /v1 (OpenAI-compatible chat completions)."""

    def __init__(self, settings, post=None):
        self.key = settings.api_key
        self.base = getattr(settings, "palgu_base", None) or PALGU_V1
        self.model = settings.research_model or "gemini-3.8-flash"
        self.structure_model = settings.structure_model or self.model
        self._post = post or _post_json

    def _chat(self, model: str, messages: list, extra=None) -> str:
        body = {"model": model, "messages": messages}
        if extra:
            body.update(extra)
        headers = {"Authorization": f"Bearer {self.key}", "x-srooter-pin": model}
        data = self._post(self.base + "/chat/completions", headers, body) or {}
        return (((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""

    def research(self, prompt: str) -> Research:
        idem = hashlib.sha256(prompt.encode()).hexdigest()[:32]
        headers = {"Authorization": f"Bearer {self.key}", "Idempotency-Key": idem}
        data = self._post(self.base + "/research", headers, {"query": prompt}) or {}
        return Research(text=data.get("text") or "", sources=_map_sources(data.get("sources")),
                        queries=list(data.get("queries") or []), model=data.get("model") or self.model)

    def research_urls(self, prompt: str) -> Research:
        return self.research(prompt)

    def deep_research(self, prompt: str) -> Research:
        return self.research(prompt)

    def structure(self, text: str, schema: dict) -> dict:
        messages = [{"role": "system", "content": "Return ONLY valid JSON matching the schema."},
                    {"role": "user", "content": f"{text}\n\nJSON schema:\n{json.dumps(schema)}"}]
        fmt = {"response_format": {"type": "json_schema",
                                   "json_schema": {"name": "stage", "schema": schema}}}
        return _extract_json(self._chat(self.structure_model, messages, fmt))
