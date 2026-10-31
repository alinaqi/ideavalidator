"""Thin Gemini wrapper: search-grounded research, JSON structuring, Deep Research."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from .grounding import deep_text, extract_sources, parse_json, search_queries

__all__ = ["GeminiClient", "Research", "extract_sources", "parse_json"]

STRUCTURE_PREFIX = (
    "You are converting research notes into strict JSON for a validation pipeline.\n"
    "Rules: use ONLY facts present in the notes; never invent sources or numbers; "
    "keep every URL exactly as written; when something is not in the notes, use "
    "'UNKNOWN' or an empty list; scores are integers 0-5 following the rubric in the "
    "notes; evidence labels: directness HIGH/MED/LOW, behavior_vs_stated "
    "BEHAVIOR/STATED/MIXED, recency FRESH/STALE.\n\nNOTES:\n"
)
POLL_SECONDS = 20
DEEP_TIMEOUT_SECONDS = 45 * 60


@dataclass
class Research:
    text: str
    sources: list = field(default_factory=list)
    queries: list = field(default_factory=list)
    model: str = ""


class GeminiClient:
    def __init__(self, settings):
        self.settings = settings
        self.model = settings.research_model
        self._client = None
        self._models = None
        self._interactions = None

    def _api(self):
        if self._client is None:
            self._client = genai.Client(api_key=self.settings.api_key)
        return self._client

    @property
    def models(self):
        return self._models or self._api().models

    @property
    def interactions(self):
        return self._interactions or self._api().interactions

    def research(self, prompt: str) -> Research:
        """Search-grounded research pass; returns prose plus cited sources."""
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
        )
        response = self.models.generate_content(
            model=self.model, contents=prompt, config=config)
        return Research(response.text or "", extract_sources(response),
                        search_queries(response), self.model)

    def research_urls(self, prompt: str) -> Research:
        """Grounded pass that reads page URLs (url_context) and fills gaps with search."""
        tools = [types.Tool(url_context=types.UrlContext()),
                 types.Tool(google_search=types.GoogleSearch())]
        config = types.GenerateContentConfig(tools=tools, temperature=0.3)
        try:
            response = self.models.generate_content(
                model=self.model, contents=prompt, config=config)
        except Exception:
            return self.research(prompt)
        return Research(response.text or "", extract_sources(response),
                        search_queries(response), self.model)

    def structure(self, text: str, schema: dict) -> dict:
        """Second pass: no tools, JSON mode, schema-constrained. One retry."""
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0.0,
        )
        last_error = None
        for _ in range(2):
            response = self.models.generate_content(
                model=self.settings.structure_model,
                contents=STRUCTURE_PREFIX + text, config=config)
            try:
                return parse_json(response.text)
            except ValueError as exc:
                last_error = exc
        raise last_error

    def deep_research(self, prompt: str) -> Research:
        """Run Gemini Deep Research in the background and wait for the report."""
        created = self.interactions.create(
            agent=self.settings.deep_agent, input=prompt, background=True)
        deadline = time.monotonic() + DEEP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            state = self.interactions.get(created.id)
            status = str(getattr(state, "status", "")).lower()
            if status == "completed":
                return Research(deep_text(state), [], [], self.settings.deep_agent)
            if status in {"failed", "cancelled"}:
                raise RuntimeError(f"deep research {status}: {created.id}")
            time.sleep(POLL_SECONDS)
        raise TimeoutError(f"deep research did not finish: {created.id}")
