"""Requirements check (contract v1, srooter#2785): the pure half. Validates the request, builds the prompts,
normalises the model's findings (fixed severities, known ids only, citations only from real research
sources) and derives the verdict. Network lives in `reqcheck_run.py`; this module is fully unit-tested.
"""
from __future__ import annotations

from . import reqcheck_prompt as _prompt

KINDS = _prompt.KINDS
build_prompt, build_evidence_prompt = _prompt.build_prompt, _prompt.build_evidence_prompt
findings_schema, research_query = _prompt.findings_schema, _prompt.research_query

_SEVERITY = {"wrong": "blocker", "contradiction": "blocker", "unclear": "major", "untestable": "major"}
MAX_INTENT, MAX_REQS, MAX_TEXT = 4000, 200, 4000


def _req_errors(reqs) -> list:
    if not isinstance(reqs, list) or not 1 <= len(reqs) <= MAX_REQS:
        return [f"requirements must be a list of 1..{MAX_REQS} items"]
    ids = [r.get("id") if isinstance(r, dict) else None for r in reqs]
    bad = [i for i, r in enumerate(reqs) if not isinstance(r, dict)
           or not str(r.get("id") or "").strip() or not isinstance(r.get("text"), str)
           or not r["text"].strip() or len(r["text"]) > MAX_TEXT]
    if bad:
        return [f"requirements[{bad[0]}] needs a non-empty id and text (<= {MAX_TEXT} chars)"]
    return ["requirement ids must be unique"] if len(set(ids)) != len(ids) else []


def validate_request(body) -> list:
    """Return the reasons a body breaks contract v1 (empty when valid)."""
    if not isinstance(body, dict):
        return ["body must be a JSON object"]
    intent = body.get("intent")
    if not isinstance(intent, str) or not intent.strip() or len(intent) > MAX_INTENT:
        return [f"intent must be a non-empty string of at most {MAX_INTENT} chars"]
    errors = _req_errors(body.get("requirements"))
    if "context" in body and not isinstance(body["context"], (dict, type(None))):
        errors.append("context must be an object")
    if body.get("depth", "quick") != "quick":
        errors.append("depth must be 'quick' (the only depth contract v1 defines)")
    return errors


def severity_for(kind: str) -> str:
    return _SEVERITY.get(kind, "minor")


def wants_research(req: dict) -> bool:
    """Grounded research only when the context says this is a new product."""
    return (req.get("context") or {}).get("existing_app") is False


def _evidence(raw, allowed_urls: set) -> list:
    return [{"url": e["url"], "quote": str(e.get("quote") or "")} for e in raw or []
            if isinstance(e, dict) and e.get("url") in allowed_urls]


def _finding(item, ids: set, allowed_urls: set):
    if not isinstance(item, dict) or item.get("kind") not in KINDS:
        return None
    message = str(item.get("message") or "").strip()
    if not message:
        return None
    rid = item.get("req_id")
    out = {"req_id": rid if rid in ids else None, "kind": item["kind"],
           "severity": severity_for(item["kind"]), "message": message}
    for key in ("question", "suggested_text"):
        if str(item.get(key) or "").strip():
            out[key] = str(item[key]).strip()
    out["evidence"] = _evidence(item.get("evidence"), allowed_urls)
    return out


def normalize(raw, req: dict, allowed_urls: set) -> list:
    """Model findings -> contract findings: known kinds/ids, fixed severity, only real citations."""
    ids = {r["id"] for r in req["requirements"]}
    found = [_finding(item, ids, allowed_urls) for item in raw or []]
    return [f for f in found if f]


def merge(main: list, extra: list) -> list:
    """Add research findings; one already flagged for the same (req_id, kind) just gains its evidence."""
    out = [dict(f) for f in main]
    index = {(f["req_id"], f["kind"]): f for f in out}
    for f in extra:
        hit = index.get((f["req_id"], f["kind"]))
        if hit is not None:
            hit["evidence"] = hit["evidence"] + f["evidence"]
        else:
            out.append(f)
    return out


def verdict(findings: list) -> str:
    severities = {f.get("severity") for f in findings}
    if "blocker" in severities:
        return "blocked"
    return "questions" if "major" in severities else "ok"
