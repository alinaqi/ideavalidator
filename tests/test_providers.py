import json

import pytest

from pipeline import providers
from pipeline.providers import REGISTRY, Chat, load_keys


def test_registry_covers_expected_providers():
    aliases = set(REGISTRY)
    assert {"openai", "anthropic-opus", "anthropic-sonnet", "gemini", "deepseek", "kimi",
            "cerebras", "groq", "xai", "glm", "minimax"} <= aliases
    for spec in REGISTRY.values():
        assert spec.base_url.startswith("https://") and spec.env_key.endswith("_API_KEY")


def test_load_keys_precedence_repo_env_then_keys_file_then_process_env(tmp_path, monkeypatch):
    for k in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "XAI_API_KEY", "IDEAVALIDATOR_KEYS_FILE"):
        monkeypatch.delenv(k, raising=False)
    keys_file = tmp_path / "other.env"
    keys_file.write_text("OPENAI_API_KEY=from-keys-file\nDEEPSEEK_API_KEY=ds\nDATABASE_URL=x\n")
    (tmp_path / ".env").write_text(f"KEYS_FILE={keys_file}\nOPENAI_API_KEY=from-root\n")
    monkeypatch.setenv("XAI_API_KEY", "from-process")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stale-shell-export")
    keys = load_keys(tmp_path)
    assert keys["OPENAI_API_KEY"] == "from-root"
    assert keys["DEEPSEEK_API_KEY"] == "ds", "explicit keys file beats ambient shell env"
    assert keys["XAI_API_KEY"] == "from-process"
    assert "DATABASE_URL" not in keys


def test_available_lists_aliases_with_keys():
    chat = Chat({"OPENAI_API_KEY": "a", "ANTHROPIC_API_KEY": "b"})
    assert set(chat.available()) == {"openai", "anthropic-opus", "anthropic-sonnet"}


def test_chat_posts_openai_payload_and_parses_content(monkeypatch):
    seen = {}

    def fake_post(url, headers, payload):
        seen.update(url=url, headers=headers, payload=payload)
        return {"choices": [{"message": {"content": "hello"}}]}

    monkeypatch.setattr(providers, "_post", fake_post)
    chat = Chat({"DEEPSEEK_API_KEY": "k1"})
    assert chat("deepseek", "sys", "usr") == "hello"
    assert seen["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer k1"
    assert seen["payload"]["model"] == REGISTRY["deepseek"].model_id
    assert seen["payload"]["messages"][0] == {"role": "system", "content": "sys"}


def test_chat_errors_for_unknown_alias_or_missing_key():
    chat = Chat({})
    with pytest.raises(KeyError):
        chat("nope", "s", "u")
    with pytest.raises(RuntimeError):
        chat("openai", "s", "u")


def test_post_handles_http_error(monkeypatch):
    import urllib.error

    def boom(req, timeout):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(providers.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError):
        providers._post("https://x.test/v1/chat/completions", {}, {"model": "m"})
