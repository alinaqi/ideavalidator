"""A drop-in replacement for GeminiClient that runs the pipeline on Palgu's OpenAI-compatible /v1 gateway,
so a signed-in user needs no GEMINI_API_KEY. research/structure are chat completions; the model is pinned
with the `x-srooter-pin` header. NOTE: grounded web search is a Gemini-native feature — until Palgu exposes
a grounded-research endpoint (tracked in a srooter issue) research here is model-native, so sources are
empty. Network is injected (`post`) for testing; it is best-effort and returns "" / {} on any failure.
"""
from __future__ import annotations

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
        text = self._chat(self.model, [{"role": "user", "content": prompt}])
        return Research(text=text, sources=[], queries=[], model=self.model)

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
