import json

import pytest

from pipeline import cli
from tests.conftest import FakeClient


def test_stages_command_lists_all(capsys):
    assert cli.main(["stages"]) == 0
    out = capsys.readouterr().out
    assert "frame" in out and "decision" in out


def test_run_subset_and_report(brief_path, tmp_path, capsys):
    runs = tmp_path / "runs"
    code = cli.main(["run", "--idea", str(brief_path), "--stages", "frame,problem",
                     "--out", str(runs)], client_factory=lambda s: FakeClient())
    assert code == 0
    assert (runs / "test-idea" / "problem.json").exists()
    assert cli.main(["report", "--idea", "test-idea", "--out", str(runs)]) == 0
    assert "Decision memo" in capsys.readouterr().out


def test_run_missing_dependency_returns_error(brief_path, tmp_path, capsys):
    code = cli.main(["run", "--idea", str(brief_path), "--stages", "market",
                     "--out", str(tmp_path)], client_factory=lambda s: FakeClient())
    assert code == 2
    assert "depends on" in capsys.readouterr().err


def test_run_without_key_fails_cleanly(brief_path, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    code = cli.main(["run", "--idea", str(brief_path), "--out", str(tmp_path)])
    assert code == 1
    assert "GEMINI_API_KEY" in capsys.readouterr().err


def test_stop_on_kill_halts_after_killed_stage(brief_path, tmp_path, capsys):
    killed = FakeClient({"summary": "s", "scores": {"actor_specificity": 1},
                         "kill_flags": ["tarpit_pattern"], "evidence": [], "unknowns": []})
    code = cli.main(["run", "--idea", str(brief_path), "--stages", "frame,problem",
                     "--out", str(tmp_path), "--stop-on-kill"], client_factory=lambda s: killed)
    assert code == 3
    assert (tmp_path / "test-idea" / "frame.json").exists()
    assert not (tmp_path / "test-idea" / "problem.json").exists()
    assert "stopped" in capsys.readouterr().out.lower()


def test_doctor_reports_missing_key_then_ok(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert cli.main(["doctor"]) == 1
    assert "missing" in capsys.readouterr().out.lower()
    (tmp_path / ".env").write_text("GEMINI_API_KEY=k\n")
    assert cli.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "9/9" in out and "gemini-3.1-pro-preview" in out
