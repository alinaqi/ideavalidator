"""Requirements check (contract v1): the network half. One structured Palgu call (json_schema) checks the
requirements; for a new product a grounded `/v1/research` call plus a short evidence pass run in
parallel and add cited findings. Every call uses the caller's key. Unlike PalguClient (best-effort, ""
on failure) this raises `CheckFailed`, so a check that did not run can never come back as verdict ok.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

from . import reqcheck as rc
from .palgu import PALGU_V1
from .palgu_client import _extract_json
from .reqcheck_prompt import research_query


class CheckFailed(Exception):
    def __init__(self, status: int, code: str, message: str, body=None):
        super().__init__(message)
        self.status, self.code, self.message, self.body = status, code, message, body


def classify_status(http_status: int) -> tuple:
    """Palgu HTTP status -> (our status, error code). 401/403 -> 401, 402 passes through, rest -> 503."""
    if http_status in (401, 403):
        return 401, "unauthorized"
    if http_status == 402:
        return 402, "payment_required"
    return 503, "palgu_unavailable"


def post_json(url: str, headers: dict, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=max(timeout, 1.0)) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        status, code = classify_status(exc.code)
        upstream = _extract_json(exc.read().decode(errors="replace")) or None
        raise CheckFailed(status, code, f"Palgu returned HTTP {exc.code}", upstream) from None
    except Exception as exc:  # noqa: BLE001 - timeout, DNS, reset, non-JSON body
        raise CheckFailed(503, "palgu_unavailable", type(exc).__name__) from None


@dataclass(frozen=True)
class Options:
    post: Callable = post_json
    base: str = PALGU_V1
    model: str = "gemini-3.8-flash"   # same default as config.Settings._palgu (PALGU_STRUCTURE_MODEL)
    budget_s: float = 40.0            # the web route kills the worker at 45 s
    research_s: float = 28.0
    clock: Callable = field(default=time.monotonic)


@dataclass(frozen=True)
class _Ctx:
    """One check in flight: the request, the caller's key, the options and the absolute deadline."""
    req: dict
    key: str
    opts: Options
    deadline: float

    def left(self) -> float:
        return self.deadline - self.opts.clock()


def _structured(ctx: _Ctx, prompt: str, schema: dict) -> tuple:
    opts = ctx.opts
    body = {"model": opts.model, "temperature": 0,
            "messages": [{"role": "system", "content": "Return ONLY valid JSON matching the schema."},
                         {"role": "user", "content": prompt}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "requirements_check", "schema": schema}}}
    headers = {"Authorization": f"Bearer {ctx.key}", "x-srooter-pin": opts.model}
    data = opts.post(opts.base + "/chat/completions", headers, body, ctx.left()) or {}
    content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    parsed = _extract_json(content)
    if not isinstance(parsed.get("findings"), list):
        raise CheckFailed(503, "check_failed", "the model returned no usable findings")
    return parsed, data.get("model") or opts.model


def _research_findings(ctx: _Ctx) -> list:
    query = research_query(ctx.req)
    headers = {"Authorization": f"Bearer {ctx.key}",
               "Idempotency-Key": hashlib.sha256(query.encode()).hexdigest()[:32]}
    url = ctx.opts.base + "/research"
    found = ctx.opts.post(url, headers, {"query": query}, min(ctx.opts.research_s, ctx.left())) or {}
    sources = [s for s in found.get("sources") or [] if isinstance(s, dict) and s.get("url")]
    if not sources:
        return []
    prompt = rc.build_evidence_prompt(ctx.req, found.get("text") or "", sources)
    parsed, _ = _structured(ctx, prompt, rc.findings_schema(True))
    return rc.normalize(parsed["findings"], ctx.req, {s["url"] for s in sources})


def _background(fn: Callable) -> tuple:
    box: dict = {}

    def target():
        try:
            box["value"] = fn()
        except Exception as exc:  # noqa: BLE001 - reported as "research skipped", never fatal
            box["error"] = getattr(exc, "code", type(exc).__name__)
    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread, box


def _error(exc: CheckFailed) -> tuple:
    if exc.status == 402 and isinstance(exc.body, dict):
        return 402, exc.body
    return exc.status, {"error": {"code": exc.code, "message": exc.message}}


def _with_research(findings: list, research, ctx: _Ctx) -> tuple:
    if research is None:
        return findings, ""
    thread, box = research
    thread.join(max(0.0, ctx.left()))
    if "value" in box:
        return rc.merge(findings, box["value"]), ""
    return findings, f"research skipped: {box.get('error', 'timeout')}"


def _precheck(req, key: str):
    errors = rc.validate_request(req)
    if errors:
        return CheckFailed(422, "invalid_body", "; ".join(errors))
    return None if key else CheckFailed(401, "unauthorized", "missing Palgu key")


def run_check(req, key: str, opts: Options = Options()) -> tuple:
    """Return (http_status, body) per contract v1."""
    start = opts.clock()
    bad = _precheck(req, key)
    if bad:
        return _error(bad)
    ctx = _Ctx(req, key, opts, start + opts.budget_s)
    research = _background(lambda: _research_findings(ctx)) if rc.wants_research(req) else None
    try:
        parsed, model = _structured(ctx, rc.build_prompt(req), rc.findings_schema())
    except CheckFailed as exc:
        return _error(exc)
    findings, note = _with_research(rc.normalize(parsed["findings"], req, set()), research, ctx)
    summary = str(parsed.get("summary") or "").strip() or f"{len(findings)} finding(s)."
    summary = f"{summary} ({note})" if note else summary
    return 200, {"verdict": rc.verdict(findings), "findings": findings, "summary": summary,
                 "model": model, "duration_ms": int((opts.clock() - start) * 1000), "contract": 1}
