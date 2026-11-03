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
    assert "10/10" in out and "gemini-3.1-pro-preview" in out


def test_council_command_runs_with_fakes(brief_path, tmp_path, capsys):
    from types import SimpleNamespace

    from tests.test_council import fake_chat_factory, fake_structurer

    out = tmp_path / "runs"
    (out / "test-idea").mkdir(parents=True)
    (out / "test-idea" / "frame.json").write_text(json.dumps({"stage": "frame", "summary": "s"}))
    code = cli.main(["council", "--idea", str(brief_path), "--out", str(out), "--rounds", "0"],
                    client_factory=lambda s: SimpleNamespace(structure=fake_structurer),
                    chat_factory=lambda keys: fake_chat_factory(["kimi", "openai"]))
    assert code == 0
    assert (out / "test-idea" / "council.json").exists()
    assert "PIVOT" in capsys.readouterr().out


def test_ingest_command_writes_brief(tmp_path, capsys):
    from tests.test_ingest import BRIEF
    ideas = tmp_path / "ideas"; ideas.mkdir()
    code = cli.main(["ingest", "--url", "https://typeform.com", "--idea", "a free survey creator",
                     "--ideas-dir", str(ideas)], client_factory=lambda s: FakeClient(structured=BRIEF))
    assert code == 0
    files = list(ideas.glob("*.md"))
    assert files and "business_model:" in files[0].read_text()
    assert "ingest" in capsys.readouterr().out.lower() or str(files[0]) in capsys.readouterr().out


def test_report_dest_writes_file_outside_run(brief_path, tmp_path):
    runs = tmp_path / "runs"
    cli.main(["run", "--idea", str(brief_path), "--stages", "frame",
              "--out", str(runs)], client_factory=lambda s: FakeClient())
    dest = tmp_path / "deliverables"
    code = cli.main(["report", "--idea", "test-idea", "--out", str(runs),
                     "--format", "html", "--dest", str(dest)])
    assert code == 0
    assert (dest / "report.html").exists()


def test_ingest_run_honours_out_dir(tmp_path, monkeypatch):
    from tests.test_ingest import BRIEF
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    ideas = tmp_path / "ideas"; ideas.mkdir()
    runs = tmp_path / "myruns"
    code = cli.main(["ingest", "--url", "https://typeform.com", "--idea", "a survey tool",
                     "--ideas-dir", str(ideas), "--out", str(runs), "--run"],
                    client_factory=lambda s: FakeClient(structured=BRIEF))
    assert code == 0
    assert list(runs.glob("*/frame.json")), "stage output should land under --out"


class _FakeFetchers:
    def search_volume(self, keywords, keys):
        from pipeline.signals import Signal
        return [Signal("dataforseo", "search_volume", "survey creator", 5400, "", "")]

    def social(self, query, keys):
        from pipeline.signals import Signal
        return [Signal("apify", "social", "best survey tool?", 14, "", "https://reddit.com/x")]


def test_signals_command_writes_signals_json(brief_path, tmp_path, monkeypatch, capsys):
    from pipeline import signals_sources
    monkeypatch.setattr(signals_sources, "default_fetchers", lambda: _FakeFetchers())
    runs = tmp_path / "runs"
    code = cli.main(["signals", "--idea", str(brief_path), "--out", str(runs)])
    assert code == 0
    data = json.loads((runs / "test-idea" / "signals.json").read_text())
    assert data["bonus"] > 0 and data["search"] and data["social"]
    assert "bonus" in capsys.readouterr().out


def test_run_default_gathers_signals(brief_path, tmp_path, monkeypatch):
    from pipeline import signals_sources
    monkeypatch.setattr(signals_sources, "default_fetchers", lambda: _FakeFetchers())
    runs = tmp_path / "runs"
    cli.main(["run", "--idea", str(brief_path), "--stages", "frame", "--out", str(runs)],
             client_factory=lambda s: FakeClient())
    assert (runs / "test-idea" / "signals.json").exists()


def test_run_no_signals_skips(brief_path, tmp_path, monkeypatch):
    from pipeline import signals_sources
    monkeypatch.setattr(signals_sources, "default_fetchers", lambda: _FakeFetchers())
    runs = tmp_path / "runs"
    cli.main(["run", "--idea", str(brief_path), "--stages", "frame", "--out", str(runs),
              "--no-signals"], client_factory=lambda s: FakeClient())
    assert not (runs / "test-idea" / "signals.json").exists()


def test_run_writes_selfcheck(brief_path, tmp_path, monkeypatch):
    from pipeline import signals_sources
    monkeypatch.setattr(signals_sources, "default_fetchers", lambda: _FakeFetchers())
    runs = tmp_path / "runs"
    cli.main(["run", "--idea", str(brief_path), "--stages", "frame", "--out", str(runs)],
             client_factory=lambda s: FakeClient())
    assert (runs / "test-idea" / "selfcheck.md").exists()


def test_selfcheck_command(brief_path, tmp_path, capsys):
    runs = tmp_path / "runs"; (runs / "test-idea").mkdir(parents=True)
    (runs / "test-idea" / "icp.json").write_text(json.dumps(
        {"beachhead": {"vertical": "Healthcare AI startups"}}))
    code = cli.main(["selfcheck", "--idea", str(brief_path), "--out", str(runs)])
    assert code == 0
    assert (runs / "test-idea" / "selfcheck.json").exists()
    assert "self-validation" in capsys.readouterr().out.lower()


def test_palgu_status_not_signed_in(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["palgu", "status"]) == 0
    assert "not signed in" in capsys.readouterr().out


def test_palgu_help_default(capsys):
    assert cli.main(["palgu"]) == 0
    assert "palgu login" in capsys.readouterr().out


def test_run_uses_palgu_provider_when_only_palgu_key(brief_path, tmp_path, monkeypatch):
    # with only PALGU_API_KEY set, make_client builds a PalguClient; stub its network
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("PALGU_API_KEY=srt_test\n")
    from pipeline import palgu_client
    monkeypatch.setattr(palgu_client, "_post_json",
                        lambda u, h, b: {"choices": [{"message": {"content": '{"summary":"s","scores":{"actor_specificity":4}}'}}]})
    runs = tmp_path / "runs"
    code = cli.main(["run", "--idea", str(brief_path), "--stages", "frame", "--out", str(runs), "--no-signals"])
    assert code == 0 and (runs / "test-idea" / "frame.json").exists()
