"""Best-effort network clients for demand signals. Every function returns [] on a missing key or any
error — signals are additive, so a dead source must never break a run. DataForSEO gives search volume;
Reddit (official API, see reddit_source) is the primary social source with Apify as fallback, and xAI
Grok covers X. Parsing is kept separate from the pure scoring in `signals`.
"""
from __future__ import annotations

import base64
import json
import re
import urllib.request
from dataclasses import dataclass

from . import reddit_source
from .signals import Signal

TIMEOUT = 60
APIFY_REDDIT_ACTOR = "trudax~reddit-scraper-lite"


def _post_json(url: str, headers: dict, payload) -> object:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _get_json(url: str, headers: dict) -> object:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def dataforseo_volume(keywords: list, keys: dict) -> list:
    """Google Ads monthly search volume per keyword via DataForSEO (Basic auth)."""
    login, pw = keys.get("DATAFORSEO_LOGIN"), keys.get("DATAFORSEO_PASSWORD")
    if not (login and pw and keywords):
        return []
    token = base64.b64encode(f"{login}:{pw}".encode()).decode()
    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"
    payload = [{"keywords": list(keywords), "location_code": 2840, "language_code": "en"}]
    body = _post_json(url, {"Authorization": f"Basic {token}"}, payload)
    rows = (((body or {}).get("tasks") or [{}])[0].get("result")) or []
    return [Signal("dataforseo", "search_volume", r.get("keyword", ""), r.get("search_volume"),
                   "Google Ads monthly volume (US)", "") for r in rows if r.get("keyword")]


def apify_reddit(query: str, keys: dict) -> list:
    """Recent Reddit threads matching the query via an Apify actor run (sync)."""
    token = keys.get("APIFY_TOKEN")
    if not token:
        return []
    url = (f"https://api.apify.com/v2/acts/{APIFY_REDDIT_ACTOR}/run-sync-get-dataset-items"
           f"?token={token}&maxItems=15")
    items = _post_json(url, {}, {"searches": [query], "maxItems": 15, "type": "posts"})
    return [Signal("apify", "social", it.get("title", "")[:120], it.get("numberOfComments"),
                   "Reddit thread", it.get("url", ""))
            for it in (items or []) if isinstance(it, dict) and it.get("title")]


def _grok_count(text: str) -> float | None:
    m = re.search(r"\d+", text or "")
    return float(m.group()) if m else None


def grok_x(query: str, keys: dict) -> list:
    """X/Twitter discussion summary via xAI Grok live search."""
    key = keys.get("XAI_API_KEY")
    if not key:
        return []
    prompt = (f"Search X/Twitter for recent discussion about: {query}. Reply with the approximate "
              "number of relevant posts first, then one line summarising the sentiment.")
    payload = {"model": "grok-4.7", "messages": [{"role": "user", "content": prompt}],
               "search_parameters": {"mode": "on", "sources": [{"type": "x"}]}}
    body = _post_json("https://api.x.ai/v1/chat/completions",
                      {"Authorization": f"Bearer {key}"}, payload)
    content = (((body or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return [Signal("grok", "social", "X discussion", _grok_count(content), content[:300], "")] \
        if content else []


@dataclass
class _DefaultFetchers:
    def search_volume(self, keywords: list, keys: dict) -> list:
        return dataforseo_volume(keywords, keys)

    def social(self, query: str, keys: dict) -> list:
        reddit = reddit_source.reddit_api(query, keys) or apify_reddit(query, keys)
        return reddit + grok_x(query, keys)


def default_fetchers() -> _DefaultFetchers:
    return _DefaultFetchers()
