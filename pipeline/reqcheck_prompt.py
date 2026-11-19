"""Requirements check: the prompts and the json_schema the structured call must follow."""
from __future__ import annotations

import json
from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"
KINDS = ("wrong", "contradiction", "unclear", "untestable", "missing", "scope_creep", "off_icp",
         "unsupported_claim")


def findings_schema(with_evidence: bool = False) -> dict:
    item = {"req_id": {"type": "string"}, "kind": {"type": "string", "enum": list(KINDS)},
            "message": {"type": "string"}, "question": {"type": "string"},
            "suggested_text": {"type": "string"}}
    if with_evidence:
        ev = {"type": "object", "properties": {"url": {"type": "string"}, "quote": {"type": "string"}},
              "required": ["url", "quote"]}
        item["evidence"] = {"type": "array", "items": ev}
    finding = {"type": "object", "properties": item, "required": ["req_id", "kind", "message"]}
    return {"type": "object", "required": ["summary", "findings"],
            "properties": {"summary": {"type": "string"},
                           "findings": {"type": "array", "items": finding}}}


def _fill(name: str, values: dict) -> str:
    text = (PROMPT_DIR / name).read_text()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _base_values(req: dict) -> dict:
    ctx = dict(req.get("context") or {})
    reqs = "\n".join(f"- {r['id']}: {r['text']}" for r in req["requirements"])
    return {"intent": req["intent"], "audience": ctx.pop("audience", None) or "not stated",
            "requirements": reqs, "context": json.dumps(ctx, ensure_ascii=False) if ctx else "none"}


def build_prompt(req: dict) -> str:
    return _fill("requirements_check.md", _base_values(req))


def build_evidence_prompt(req: dict, research_text: str, sources: list) -> str:
    urls = "\n".join(f"- {s['url']}" for s in sources if s.get("url")) or "none"
    return _fill("requirements_evidence.md",
                 {**_base_values(req), "research": research_text or "none", "sources": urls})


def research_query(req: dict) -> str:
    """Short grounded-search query (long ones take 40 s+): facts about the product, not each requirement.
    The evidence pass then compares the cited facts with the requirements."""
    v = _base_values(req)
    return (f"In under 200 words, with sources: the laws, platform rules, technical limits and market "
            f"facts that apply to building this product. Product: {v['intent'][:1500]} "
            f"Audience: {v['audience'][:300]}")
