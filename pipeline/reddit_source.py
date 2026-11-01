"""Reddit demand signals via the official app-only OAuth API (script app: client id + secret).

Best-effort: no creds or any error yields []. Credentials come from the ideaminer service
(REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT), read via providers.load_keys.
"""
from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request

from .signals import Signal

TIMEOUT = 30
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
SEARCH_URL = "https://oauth.reddit.com/search"


def _ua(keys: dict) -> str:
    return keys.get("REDDIT_USER_AGENT") or "ideavalidator/0.1"


def _token(keys: dict) -> str | None:
    cid, sec = keys.get("REDDIT_CLIENT_ID"), keys.get("REDDIT_CLIENT_SECRET")
    if not (cid and sec):
        return None
    auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST", headers={
        "Authorization": f"Basic {auth}", "User-Agent": _ua(keys),
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode()).get("access_token")
    except Exception:
        return None


def _search_json(token: str, query: str, ua: str) -> object:
    q = urllib.parse.urlencode({"q": query, "limit": 15, "sort": "relevance", "type": "link"})
    req = urllib.request.Request(f"{SEARCH_URL}?{q}",
                                 headers={"Authorization": f"Bearer {token}", "User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _to_signal(d: dict) -> Signal:
    return Signal("reddit", "social", d.get("title", "")[:120], d.get("num_comments"),
                  f"r/{d.get('subreddit', '')}", "https://www.reddit.com" + d.get("permalink", ""))


def reddit_api(query: str, keys: dict) -> list:
    """Search Reddit for the query; each matching thread becomes a social Signal (value = comments)."""
    token = _token(keys)
    if not token:
        return []
    data = _search_json(token, query, _ua(keys)) or {}
    children = ((data.get("data") or {}).get("children")) or []
    return [_to_signal(c.get("data") or {}) for c in children if (c.get("data") or {}).get("title")]
