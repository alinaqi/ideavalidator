"""NDJSON progress contract for the Rust-spawned Python worker (RED→GREEN)."""
from __future__ import annotations

import json
from pathlib import Path

from worker.run_job import Engine, RunJob, WorkerSpec, _stage_event, run_safely, verify_token


class _Stage:
    def __init__(self, sid: str) -> None:
        self.id = sid


def _fake_engine(stage_ids, gate=None, raise_on=None) -> Engine:
    gate = gate or {"verdict": "GO", "score": 4.2}

    def run_stage(stage, ctx):
        if raise_on and stage.id == raise_on:
            raise RuntimeError("boom")
        return {"gate": gate}

    return Engine(
        load_brief=lambda p: type("B", (), {"slug": "demo"})(),
        make_ctx=lambda brief, out_dir: {"brief": brief, "out": out_dir},
        resolve=lambda sel: [_Stage(s) for s in stage_ids],
        run_stage=run_stage,
    )


def _collect():
    lines: list[str] = []
    return lines, lines.append


def test_emits_stage_then_done() -> None:
    lines, emit = _collect()
    spec = WorkerSpec(Path("b.md"), Path("/out"), "all")
    RunJob(spec, _fake_engine(["frame", "problem"]), emit).execute()
    events = [json.loads(line) for line in lines]
    assert events[0] == {"event": "stage", "stage": "frame", "verdict": "GO", "score": 4.2}
    assert events[-1] == {"event": "done"}
    assert len([e for e in events if e["event"] == "stage"]) == 2


def test_error_event_on_stage_failure() -> None:
    lines, emit = _collect()
    spec = WorkerSpec(Path("b.md"), Path("/out"))
    RunJob(spec, _fake_engine(["frame"], raise_on="frame"), emit).execute()
    events = [json.loads(line) for line in lines]
    assert events[-1]["event"] == "error"
    assert "boom" in events[-1]["error"]


def test_cancel_stops_before_stage() -> None:
    lines, emit = _collect()
    spec = WorkerSpec(Path("b.md"), Path("/out"))
    RunJob(spec, _fake_engine(["frame", "problem"]), emit, is_cancelled=lambda: True).execute()
    events = [json.loads(line) for line in lines]
    assert events == [{"event": "cancelled"}]


def test_run_safely_emits_error_when_setup_fails() -> None:
    lines, emit = _collect()

    def boom() -> Engine:
        raise RuntimeError("no palgu token")

    run_safely(WorkerSpec(Path("b.md"), Path("/out")), boom, emit)
    events = [json.loads(line) for line in lines]
    assert events[-1]["event"] == "error"
    assert "no palgu token" in events[-1]["error"]


def test_run_safely_runs_the_engine_when_setup_succeeds() -> None:
    lines, emit = _collect()
    engine = _fake_engine(["frame"])
    run_safely(WorkerSpec(Path("b.md"), Path("/out")), lambda: engine, emit)
    events = [json.loads(line) for line in lines]
    assert events[-1] == {"event": "done"}


def test_verify_token_accepts_ok_envelope() -> None:
    assert verify_token(lambda: {"ok": True, "status": 200, "body": {}}) is None


def test_verify_token_blocks_on_401() -> None:
    reason = verify_token(lambda: {"ok": False, "status": 401, "body": {}})
    assert reason is not None
    assert "sign in again" in reason.lower()


def test_verify_token_ignores_transient_failure() -> None:
    assert verify_token(lambda: {"ok": False, "status": 503, "body": {}}) is None

    def boom() -> dict:
        raise OSError("no network")

    assert verify_token(boom) is None


def test_stage_event_shape() -> None:
    assert _stage_event("market", {"verdict": "KILL", "score": 1.0}) == {
        "event": "stage", "stage": "market", "verdict": "KILL", "score": 1.0}
