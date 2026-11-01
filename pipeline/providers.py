"""Multi-provider chat over OpenAI-compatible endpoints (idea borrowed from eduBITES soundingBoard).

Keys are read from the repo .env, then an optional external env file (`KEYS_FILE=` in .env or
`IDEAVALIDATOR_KEYS_FILE`), then the process environment. Explicit config beats ambient shell exports,
which are often stale.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import load_env

TIMEOUT_SECONDS = 240


@dataclass(frozen=True)
class ModelSpec:
    alias: str
    provider: str
    model_id: str
    base_url: str
    env_key: str


REGISTRY = {s.alias: s for s in (
    ModelSpec("openai", "OpenAI", "gpt-5.5", "https://api.openai.com/v1", "OPENAI_API_KEY"),
    ModelSpec("anthropic-opus", "Anthropic", "claude-opus-5-5",
              "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY"),
    ModelSpec("anthropic-sonnet", "Anthropic", "claude-sonnet-5-5",
              "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY"),
    ModelSpec("gemini", "Google", "gemini-3.1-pro-preview",
              "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    ModelSpec("deepseek", "DeepSeek", "deepseek-v4-pro", "https://api.deepseek.com/v1",
              "DEEPSEEK_API_KEY"),
    ModelSpec("kimi", "Moonshot", "kimi-k3.1-pro", "https://api.moonshot.ai/v1", "MOONSHOT_API_KEY"),
    ModelSpec("cerebras", "Cerebras", "qwen-3.8-27b", "https://api.cerebras.ai/v1",
              "CEREBRAS_API_KEY"),
    ModelSpec("groq", "Groq", "openai/gpt-oss-120b", "https://api.groq.com/openai/v1",
              "GROQ_API_KEY"),
    ModelSpec("xai", "xAI", "grok-4.7", "https://api.x.ai/v1", "XAI_API_KEY"),
    ModelSpec("glm", "Zhipu", "glm-5.3", "https://open.bigmodel.cn/api/paas/v4", "GLM_API_KEY"),
    ModelSpec("minimax", "MiniMax", "MiniMax-M3", "https://api.minimax.io/v1", "MINIMAX_API_KEY"),
)}
PROVIDER_ENV_KEYS = sorted({s.env_key for s in REGISTRY.values()})


def _keys_file(root: Path, root_env: dict) -> dict:
    path = os.environ.get("IDEAVALIDATOR_KEYS_FILE") or root_env.get("KEYS_FILE") or ""
    return load_env(Path(path).expanduser()) if path else {}


def load_keys(root: Path, names=None) -> dict:
    """Named keys (default: provider keys); precedence: repo .env > external keys file > process env."""
    root_env = load_env(root / ".env")
    external = _keys_file(root, root_env)
    keys = {}
    for name in names or PROVIDER_ENV_KEYS:
        value = root_env.get(name) or external.get(name) or os.environ.get(name)
        if value:
            keys[name] = value
    return keys


def _post(url: str, headers: dict, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{url} → HTTP {exc.code}: {exc.read()[:300]!r}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"{url} → {exc}") from exc


class Chat:
    """Callable: chat(alias, system, user) -> assistant text."""

    def __init__(self, keys: dict):
        self.keys = keys

    def available(self) -> list:
        return [a for a, s in REGISTRY.items() if self.keys.get(s.env_key)]

    def __call__(self, alias: str, system: str, user: str) -> str:
        spec = REGISTRY[alias]
        key = self.keys.get(spec.env_key)
        if not key:
            raise RuntimeError(f"no key for {alias} ({spec.env_key})")
        payload = {"model": spec.model_id, "messages": [
            {"role": "system", "content": system}, {"role": "user", "content": user}]}
        headers = {"Authorization": f"Bearer {key}", "x-api-key": key}
        data = _post(f"{spec.base_url}/chat/completions", headers, payload)
        choice = (data.get("choices") or [{}])[0]
        return (choice.get("message") or {}).get("content") or ""
