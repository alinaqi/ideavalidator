import pytest

from pipeline.config import MissingKeyError, Settings, load_env


def test_load_env_parses_pairs_and_ignores_comments(tmp_path):
    p = tmp_path / ".env"
    p.write_text("# c\nGEMINI_API_KEY=abc\n\nGEMINI_MODEL=m1\nBAD LINE\n")
    assert load_env(p) == {"GEMINI_API_KEY": "abc", "GEMINI_MODEL": "m1"}


def test_load_env_missing_file_returns_empty(tmp_path):
    assert load_env(tmp_path / "nope") == {}


def test_settings_defaults_and_overrides(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_STRUCTURE_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_DEEP_RESEARCH_AGENT", raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=k\nGEMINI_MODEL=custom\n")
    s = Settings.from_env(tmp_path)
    assert s.api_key == "k"
    assert s.research_model == "custom"
    assert s.structure_model == "gemini-3.8-flash"
    assert s.deep_agent.startswith("deep-research")
    assert s.root == tmp_path


def test_settings_process_env_wins_over_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fromenv")
    (tmp_path / ".env").write_text("GEMINI_API_KEY=fromfile\n")
    assert Settings.from_env(tmp_path).api_key == "fromenv"


def test_settings_missing_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(MissingKeyError):
        Settings.from_env(tmp_path)
