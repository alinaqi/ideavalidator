import json

import pytest

from pipeline.ingest import BRIEF_SCHEMA, IngestRequest, build_brief, slugify
from tests.conftest import FakeClient

BRIEF = {
    "title": "Zenloop — free survey creator",
    "one_sentence_pitch": "SMBs can create NPS surveys free.",
    "business_model": "plg_freemium", "success_definition": "compounding_product",
    "validation_mode": "existing_market", "company_summary": "Zenloop is a CX/NPS platform.",
    "thesis_spine": {"core_mechanism": "free tool → upsell", "moat_end_state": "data graph",
                     "non_negotiables": ["free tier", "self-serve"]},
    "actor": "SMB CX manager", "job": "measure customer satisfaction",
    "current_workaround_and_cost": "Google Forms, manual", "why_now": "AI makes it cheap",
    "why_us": "existing zenloop audience", "candidate_verticals": ["ecommerce", "SaaS"],
    "value_metric": "per response", "price_hypothesis": "$0 free, paid tiers",
    "channel": "zenloop newsletter", "risks": ["free incumbents"], "out_of_scope": ["enterprise"],
}


def test_slugify_from_domain_and_angle():
    assert slugify(IngestRequest("https://zenloop.com", "a free survey creator")).startswith("zenloop-")
    assert "survey" in slugify(IngestRequest("https://zenloop.com", "a free survey creator"))
    assert slugify(IngestRequest("https://www.zenloop.com/", "")) == "zenloop"


def test_explicit_slug_wins():
    assert slugify(IngestRequest("https://x.com", "y", "custom-slug")) == "custom-slug"


def test_brief_schema_has_core_fields():
    props = BRIEF_SCHEMA["properties"]
    for k in ("title", "business_model", "success_definition", "validation_mode", "thesis_spine",
              "candidate_verticals", "why_us"):
        assert k in props


def test_build_brief_renders_template_with_frontmatter_and_angle():
    client = FakeClient(structured=BRIEF)
    slug, md = build_brief(client, IngestRequest("https://zenloop.com", "a free survey creator"))
    assert slug.startswith("zenloop-")
    assert md.startswith("---")
    assert "business_model: plg_freemium" in md
    assert "success_definition: compounding_product" in md
    assert "validation_mode: existing_market" in md
    assert "free survey creator" in md  # the angle/idea
    assert "Zenloop is a CX/NPS platform" in md  # company summary from the site
    assert "## Thesis spine" in md and "free tool" in md
    assert "ecommerce" in md  # candidate verticals
    # the model was told the url AND the angle
    assert "https://zenloop.com" in client.prompts[0] and "free survey creator" in client.prompts[0]


def test_build_brief_without_angle_validates_the_company_itself():
    client = FakeClient(structured=BRIEF)
    slug, md = build_brief(client, IngestRequest("https://zenloop.com", ""))
    assert slug == "zenloop"
    # prompt should instruct validating the company's own business when no angle given
    p = client.prompts[0].lower()
    assert "https://zenloop.com" in client.prompts[0]
    assert "own business" in p or "the company's" in p or "what the company" in p


def test_loader_can_parse_the_generated_brief(tmp_path):
    from pipeline.prompts import load_brief
    client = FakeClient(structured=BRIEF)
    slug, md = build_brief(client, IngestRequest("https://zenloop.com", "a free survey creator"))
    f = tmp_path / f"{slug}.md"; f.write_text(md)
    b = load_brief(f)
    assert b.business_model == "plg_freemium"
    assert b.success_definition == "compounding_product"
    assert b.validation_mode == "existing_market"
