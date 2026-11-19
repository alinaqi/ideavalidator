"""Shared loaders for the requirements-check contract fixtures (also read by the Rust contract tests)."""
import copy
import json
from pathlib import Path

FIX = Path(__file__).parent / "fixtures" / "requirements_check"


def load(name: str):
    return json.loads((FIX / name).read_text())


def _expand(body):
    body = copy.deepcopy(body)
    if isinstance(body, dict) and body.get("intent") == "@LONG4001@":
        body["intent"] = "x" * 4001
    if isinstance(body, dict) and body.get("requirements") == "@201REQS@":
        body["requirements"] = [{"id": f"R-{i}", "text": "x"} for i in range(201)]
    return body


def invalid_bodies():
    return [(case["name"], _expand(case["body"])) for case in load("invalid_bodies.json")]
