import json

import pytest

from pipeline.council import (CouncilContext, assemble_board, board_dossier,
                              load_personas, parse_vote, run_council)
from pipeline.prompts import load_brief


def fake_chat_factory(available):
    calls = []

    def chat(alias, system, user):
        calls.append((alias, system, user))
        if system.startswith("You chair"):
            return "## Consensus\nfine\n## Votes\n- Bootstrapper GO"
        if system.startswith("You are the Red Team"):
            return "Red Team: do nothing yet\n\nThe board shares X.\n\nVote: PIVOT"
        if "continuing as" in system:
            return "I now agree partly.\nVote: PIVOT"
        return f"Framework: Mom Test\n\nPosition from {alias}.\n\nVote: GO\nEnrichment: narrow to dentists\nVerify: no-show rate"

    chat.available = lambda: list(available)
    chat.calls = calls
    return chat


def fake_structurer(text, schema):
    assert "Consensus" in text and schema["type"] == "object"
    return {"summary": "synth", "votes": [{"role": "Bootstrapper", "vote": "GO"}],
            "recommendation": {"verdict": "PIVOT", "rationale": "r"}, "claims_to_verify": []}


def test_personas_load_with_models_and_frameworks():
    members, red, chair = load_personas()
    assert len(members) >= 5
    for p in members:
        assert p.models and p.frameworks and len(p.system_prompt) > 100
    assert red.role == "Red Team" and chair.models


def test_assemble_board_prefers_listed_models_then_falls_back():
    members, _, _ = load_personas()
    board = assemble_board(members, ["kimi", "gemini"])
    aliases = [seat.alias for seat in board]
    assert len(board) == len(members)
    assert set(aliases) <= {"kimi", "gemini"}
    assert board[0].alias == "kimi"  # Bootstrapper prefers kimi over gemini
    assert assemble_board(members, []) == []


def test_parse_vote_and_framework():
    text = "Framework: Premortem\n\nbody\n\nVote: KILL\nEnrichment: x\nVerify: y"
    parsed = parse_vote(text)
    assert parsed == {"framework": "Premortem", "vote": "KILL", "enrichment": "x", "verify": "y"}
    assert parse_vote("no labels")["vote"] == "UNKNOWN"


def test_board_dossier_includes_brief_stage_summaries_and_evidence(brief_path, seeded_out_dir):
    dossier = board_dossier(load_brief(brief_path), seeded_out_dir)
    assert "SMS waitlists" in dossier
    assert "summary for frame" in dossier and "summary for problem" in dossier
    assert "no-show rates" in dossier and "BEHAVIOR" in dossier


def test_run_council_end_to_end_with_fakes(brief_path, seeded_out_dir):
    chat = fake_chat_factory(["kimi", "gemini", "openai"])
    ctx = CouncilContext(brief=load_brief(brief_path), out_dir=seeded_out_dir, chat=chat,
                         structurer=fake_structurer, rounds=1, red_team=True)
    data = run_council(ctx)
    assert (seeded_out_dir / "council.json").exists() and (seeded_out_dir / "council.md").exists()
    assert len(data["members"]) >= 5
    assert all(m["framework"] == "Mom Test" and m["vote"] == "GO" for m in data["members"])
    assert len(data["debate"]) == len(data["members"])
    assert data["red_team"]["vote"] == "PIVOT" and data["red_team"]["position"] == "do nothing yet"
    assert data["synthesis"]["recommendation"]["verdict"] == "PIVOT"
    assert data["summary"] == "synth"
    systems = [c[1] for c in chat.calls]
    assert any("Bootstrapper" in s or "bootstrapped founder" in s for s in systems)
    assert "summary for frame" in chat.calls[0][2]


def test_run_council_without_models_raises(brief_path, out_dir):
    chat = fake_chat_factory([])
    ctx = CouncilContext(brief=load_brief(brief_path), out_dir=out_dir, chat=chat,
                         structurer=fake_structurer)
    with pytest.raises(RuntimeError):
        run_council(ctx)


def test_member_failure_is_isolated(brief_path, seeded_out_dir):
    chat = fake_chat_factory(["kimi", "openai"])
    inner = chat

    def flaky(alias, system, user):
        if alias == "openai" and "Framework" in system:
            raise RuntimeError("provider down")
        return inner(alias, system, user)

    flaky.available = inner.available
    flaky.calls = inner.calls
    ctx = CouncilContext(brief=load_brief(brief_path), out_dir=seeded_out_dir, chat=flaky,
                         structurer=fake_structurer, rounds=0, red_team=False)
    data = run_council(ctx)
    errors = [m for m in data["members"] if m.get("error")]
    assert errors and all(m["model"] == "openai" for m in errors)
    assert data["debate"] == [] and data["red_team"] is None


def test_chair_and_red_team_fall_back_to_next_model_on_failure(brief_path, seeded_out_dir):
    inner = fake_chat_factory(["anthropic-opus", "openai", "kimi"])

    def flaky(alias, system, user):
        if alias == "anthropic-opus":
            raise RuntimeError("HTTP 401 invalid key")
        return inner(alias, system, user)

    flaky.available = inner.available
    flaky.calls = inner.calls
    ctx = CouncilContext(brief=load_brief(brief_path), out_dir=seeded_out_dir, chat=flaky,
                         structurer=fake_structurer, rounds=0, red_team=True)
    data = run_council(ctx)
    assert data["red_team"]["model"] == "openai" and data["red_team"]["vote"] == "PIVOT"
    assert data["chair_model"] == "openai"
    assert data["synthesis"]["recommendation"]["verdict"] == "PIVOT"


def test_council_survives_total_synthesis_failure(brief_path, seeded_out_dir):
    inner = fake_chat_factory(["kimi"])

    def no_chair(alias, system, user):
        if system.startswith("You chair"):
            raise RuntimeError("down")
        return inner(alias, system, user)

    no_chair.available = inner.available
    no_chair.calls = inner.calls
    ctx = CouncilContext(brief=load_brief(brief_path), out_dir=seeded_out_dir, chat=no_chair,
                         structurer=fake_structurer, rounds=0, red_team=False)
    data = run_council(ctx)
    assert data["synthesis"] == {} and "down" in data["synthesis_error"]
    assert (seeded_out_dir / "council.json").exists()
