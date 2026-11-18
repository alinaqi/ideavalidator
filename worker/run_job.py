"""Thin worker the Rust service spawns per validation run. It drives the existing, tested pipeline
engine (one stage at a time) and emits one NDJSON line per event to stdout, which Rust reads to update
Postgres + Server-Sent Events. The engine is reused unchanged; only progress emission is added here.

Events (one JSON object per line):
    {"event":"stage","stage":"market","verdict":"GO","score":4.2}
    {"event":"done"}
    {"event":"cancelled"}
    {"event":"error","error":"..."}

`RunJob` is pure and injectable (engine + emit + cancel), so the contract is unit-tested without the
real engine or any Palgu call; `main()` wires the real engine and stdout.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class WorkerSpec:
    brief_path: Path
    out_root: Path
    stages: str = "all"


@dataclass(frozen=True)
class Engine:
    load_brief: Callable        # (path) -> brief (has .slug)
    make_ctx: Callable          # (brief, out_dir) -> ctx
    resolve: Callable           # (selection) -> list[stage] (each has .id)
    run_stage: Callable         # (stage, ctx) -> {"gate": {"verdict", "score"}}


def _stage_event(stage_id: str, gate: dict) -> dict:
    return {"event": "stage", "stage": stage_id,
            "verdict": gate.get("verdict"), "score": gate.get("score")}


@dataclass(frozen=True)
class RunJob:
    spec: WorkerSpec
    engine: Engine
    emit: Callable[[str], None]
    is_cancelled: Callable[[], bool] = lambda: False

    def execute(self) -> None:
        """Run the stages and emit progress. Never raises: failures become an error event."""
        try:
            self._run()
        except Exception as exc:  # surface any engine failure as the run's error event
            self._event({"event": "error", "error": str(exc)})

    def _run(self) -> None:
        brief = self.engine.load_brief(self.spec.brief_path)
        ctx = self.engine.make_ctx(brief, Path(self.spec.out_root) / brief.slug)
        for stage in self.engine.resolve(self.spec.stages):
            if self.is_cancelled():
                return self._event({"event": "cancelled"})
            gate = self.engine.run_stage(stage, ctx)["gate"]
            self._event(_stage_event(stage.id, gate))
        self._event({"event": "done"})

    def _event(self, payload: dict) -> None:
        self.emit(json.dumps(payload))


def _real_engine(client, deep: bool = False) -> Engine:
    from pipeline.prompts import load_brief
    from pipeline.runner import RunContext, run_stage
    from pipeline.stages import resolve
    return Engine(
        load_brief=load_brief,
        make_ctx=lambda brief, out_dir: RunContext(
            brief=brief, out_dir=out_dir, client=client, deep=deep),
        resolve=resolve,
        run_stage=run_stage,
    )


def _client_from_env(root: Path):
    from pipeline.config import Settings, make_client
    return make_client(Settings._palgu(os.environ.get("PALGU_API_KEY", ""), {}, root))


def _emit_stdout(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def run_safely(
    spec: WorkerSpec,
    build_engine: Callable[[], Engine],
    emit: Callable[[str], None],
) -> None:
    """Build the engine and run; a setup failure becomes an error event, not a silent exit."""
    try:
        engine = build_engine()
    except Exception as exc:  # bad/expired token, missing dep, bad brief path
        emit(json.dumps({"event": "error", "error": f"worker setup failed: {exc}"}))
        return
    RunJob(spec, engine, emit).execute()


def verify_token(me_call: Callable[[], dict]) -> "str | None":
    """None if the run may proceed; a human reason only when Palgu *definitively* rejects the key.
    A transient `/me` failure (network, 5xx) returns None so a valid key is never blocked by a blip."""
    try:
        res = me_call()
    except Exception:
        return None
    if res.get("ok"):
        return None
    if res.get("status") in (401, 403):
        return "Palgu rejected your sign-in — your key is invalid or expired. Sign out and sign in again."
    return None


def _me_call() -> dict:
    from pipeline.palgu_run import _Http
    return _Http().get("/me", os.environ.get("PALGU_API_KEY", ""))


def _parse(argv) -> "object":
    import argparse
    parser = argparse.ArgumentParser(prog="worker.run_job", description=__doc__)
    parser.add_argument("--brief", required=True, help="path to the idea brief markdown")
    parser.add_argument("--out", required=True, help="run output root dir")
    parser.add_argument("--stages", default="all", help="'all' or comma list of stage ids")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse(argv)
    root = Path(__file__).resolve().parents[1]
    spec = WorkerSpec(Path(args.brief), Path(args.out), args.stages)
    print(f"worker: starting run for {spec.brief_path}", file=sys.stderr, flush=True)
    reason = verify_token(_me_call)
    if reason:
        print(f"worker: {reason}", file=sys.stderr, flush=True)
        _emit_stdout(json.dumps({"event": "error", "error": reason}))
        return 0
    run_safely(spec, lambda: _real_engine(_client_from_env(root)), _emit_stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
