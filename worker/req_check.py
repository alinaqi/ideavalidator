"""Worker the Rust service spawns per requirements check (ADR 0014). Reads one contract-v1 request as JSON
on stdin, takes the caller's Palgu key from PALGU_API_KEY, and writes exactly one JSON line to stdout:
`{"status": <http status>, "body": <response body>}`. Logs carry counts only: never the key, never the
requirement text. Any crash becomes a 503 line, so the caller can never mistake it for verdict ok.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pipeline.reqcheck_run import Options, run_check


def _options() -> Options:
    from pipeline.config import Settings
    s = Settings._palgu("", {}, Path(__file__).resolve().parents[1])
    return Options(base=s.palgu_base, model=s.structure_model)


def _counts(req) -> str:
    if not isinstance(req, dict):
        return "requirements=?"
    reqs = req.get("requirements")
    ctx = req.get("context") if isinstance(req.get("context"), dict) else {}
    research = ctx.get("existing_app") is False
    return f"requirements={len(reqs) if isinstance(reqs, list) else '?'} research={research}"


def _respond(status: int, body: dict) -> int:
    sys.stdout.write(json.dumps({"status": status, "body": body}) + "\n")
    sys.stdout.flush()
    return 0


def main() -> int:
    try:
        req = json.loads(sys.stdin.read())
    except ValueError:
        return _respond(422, {"error": {"code": "invalid_body", "message": "body is not valid JSON"}})
    print(f"req_check: start {_counts(req)}", file=sys.stderr, flush=True)
    try:
        status, body = run_check(req, os.environ.get("PALGU_API_KEY", ""), _options())
    except Exception as exc:  # noqa: BLE001 - never let a crash read as "ok"
        print(f"req_check: crashed ({type(exc).__name__})", file=sys.stderr, flush=True)
        return _respond(503, {"error": {"code": "check_failed", "message": "the check crashed"}})
    detail = body.get("verdict") or (body.get("error") or {}).get("code", "")
    print(f"req_check: done status={status} {detail} findings={len(body.get('findings') or [])} "
          f"ms={body.get('duration_ms', '-')}", file=sys.stderr, flush=True)
    return _respond(status, body)


if __name__ == "__main__":
    sys.exit(main())
