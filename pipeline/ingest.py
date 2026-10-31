"""Turn a website URL (+ optional angle) into a validation brief, agentically.

Two modes: with an angle the IDEA is the angle and the site supplies context/why-us/market; with no
angle the company's own business (as the site describes it) is the idea. Gemini reads the site via the
url_context tool and fills gaps with search, then the result is structured into the brief template."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

BRIEF_SCHEMA = json.loads((Path(__file__).parent / "schemas" / "brief.json").read_text())
_STOP = {"a", "an", "the", "for", "to", "of", "and", "free", "that", "with"}


@dataclass
class IngestRequest:
    url: str
    angle: str = ""
    slug: str = ""


def _domain(url: str) -> str:
    host = urlparse(url if "//" in url else f"//{url}").netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    return (host.split(".")[0] or "idea") if host else "idea"


def slugify(req: IngestRequest) -> str:
    if req.slug:
        return req.slug
    base = _domain(req.url)
    words = [w for w in re.findall(r"[a-z0-9]+", req.angle.lower()) if w not in _STOP][:4]
    return f"{base}-{'-'.join(words)}" if words else base


def _prompt(req: IngestRequest) -> str:
    common = (f"Read the website {req.url} (use the URL tool) and research the company with search. "
              "Extract what it does, its product(s), customers, pricing if visible, geography and "
              "competitors. Then produce the validation-brief JSON. Classify business_model and, if you "
              "can, success_definition and validation_mode (else leave blank). Write a Thesis spine "
              "(core mechanism, moat/end-state, non-negotiables). Never invent facts not on the site or "
              "in sources; use UNKNOWN where unsure.")
    if req.angle.strip():
        return (f"{common}\n\nThe IDEA to validate is: \"{req.angle.strip()}\" — as a new product for, or "
                f"inspired by, the company at {req.url}. Use the company as context, audience and why-us; "
                "the idea itself is the angle, not the company's current business.")
    return (f"{common}\n\nThe IDEA to validate is the company's OWN business as the site describes it "
            "(what the company actually does). Frame the brief around validating that business.")


def _fm(data: dict, slug: str, req: IngestRequest) -> str:
    rows = [f"slug: {slug}", f"title: {data.get('title', slug)}", f"date: {date.today().isoformat()}",
            "author: ingested from URL", f"source_url: {req.url}", "status: ingested"]
    for k in ("business_model", "success_definition", "validation_mode"):
        v = str(data.get(k, "") or "").strip()
        if v and v.upper() != "UNKNOWN":
            rows.append(f"{k}: {v}")
    return "---\n" + "\n".join(rows) + "\n---"


def _spine(data: dict) -> str:
    sp = data.get("thesis_spine", {}) or {}
    nn = "; ".join(sp.get("non_negotiables", []) or [])
    return (f"- Core mechanism: {sp.get('core_mechanism', 'UNKNOWN')}\n"
            f"- Intended moat / end-state: {sp.get('moat_end_state', 'UNKNOWN')}\n"
            f"- Non-negotiables: {nn or 'UNKNOWN'}")


def _bullets(items) -> str:
    return "\n".join(f"- {x}" for x in (items or [])) or "- UNKNOWN"


_BODY = [
    ("One-sentence pitch", "one_sentence_pitch"), ("Target actor and context (hypothesis)", "actor"),
    ("Job to be done", "job"),
    ("Current workaround / status quo and what it costs them", "current_workaround_and_cost"),
    ("Why now", "why_now"), ("Why us", "why_us"),
]


def _model_section(data: dict) -> str:
    return ("## Business model hypothesis\n"
            f"- Value metric: {data.get('value_metric', 'UNKNOWN')}\n"
            f"- Price point: {data.get('price_hypothesis', 'UNKNOWN')}\n"
            f"- Channel: {data.get('channel', 'UNKNOWN')}")


def _sections(data: dict, req: IngestRequest) -> list:
    out = [f"# Idea brief\n\n_Auto-ingested from {req.url}. Company context: "
           f"{data.get('company_summary', 'UNKNOWN')}_",
           f"## Thesis spine (the parts that must NOT be silently dropped later)\n{_spine(data)}"]
    if req.angle.strip():
        out.append(f"## The idea being validated (for this company)\n{req.angle.strip()}")
    out += [f"## {h}\n{data.get(k, 'UNKNOWN')}" for h, k in _BODY]
    out.append("## Candidate verticals / segments to consider\n" + _bullets(data.get("candidate_verticals")))
    out += [_model_section(data), "## Known risks / open questions\n" + _bullets(data.get("risks")),
            "## Out of scope\n" + _bullets(data.get("out_of_scope"))]
    return out


def render_brief(data: dict, slug: str, req: IngestRequest) -> str:
    return _fm(data, slug, req) + "\n\n" + "\n\n".join(_sections(data, req)) + "\n"


def build_brief(client, req: IngestRequest) -> tuple:
    slug = slugify(req)
    research = client.research_urls(_prompt(req))
    cites = "\n".join(f"- {s.get('title') or s['url']}: {s['url']}" for s in research.sources)
    data = client.structure(f"{research.text}\n\nSOURCES:\n{cites}", BRIEF_SCHEMA)
    return slug, render_brief(data, slug, req)
