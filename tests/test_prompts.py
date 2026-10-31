import pytest

from pipeline.prompts import Brief, load_brief, load_schema, render
from pipeline.stages import STAGES, get_stage


def test_load_brief_parses_frontmatter_and_body(brief_path):
    b = load_brief(brief_path)
    assert isinstance(b, Brief)
    assert b.slug == "test-idea"
    assert b.title == "Test Idea"
    assert "SMS waitlists" in b.body
    assert "---" not in b.body.split("# Idea brief")[0]


def test_load_brief_without_frontmatter_uses_filename(tmp_path):
    p = tmp_path / "plain-idea.md"
    p.write_text("# Just a body\n")
    b = load_brief(p)
    assert b.slug == "plain-idea"
    assert b.title == "plain-idea"


def test_render_substitutes_brief_prior_and_title(brief_path):
    b = load_brief(brief_path)
    txt = render(get_stage("problem"), b, {"frame": "FRAME SUMMARY"})
    assert "SMS waitlists" in txt
    assert "FRAME SUMMARY" in txt
    assert "Test Idea" in txt
    assert "{{" not in txt


def test_every_stage_has_template_and_schema(brief_path):
    b = load_brief(brief_path)
    for s in STAGES:
        txt = render(s, b, {})
        assert len(txt) > 400, s.id
        schema = load_schema(s)
        props = schema["properties"]
        for key in ("summary", "scores", "kill_flags", "evidence", "unknowns"):
            assert key in props, (s.id, key)


def test_schema_scores_match_gate_rules():
    from pipeline.gates import RULES

    for s in STAGES:
        score_props = set(load_schema(s)["properties"]["scores"]["properties"])
        assert set(RULES[s.id].criteria) <= score_props, s.id


def test_render_missing_template_raises(brief_path):
    from pipeline.stages import Stage

    fake = Stage("nope", "Nope", "S0", (), "Why?")
    with pytest.raises(FileNotFoundError):
        render(fake, load_brief(brief_path), {})


def test_render_injects_business_model_and_success_tokens(tmp_path):
    from pipeline.prompts import load_brief
    p = tmp_path / "i.md"
    p.write_text("---\nslug: i\nbusiness_model: plg_freemium_directory\n"
                 "success_definition: compounding_product\n---\n# Idea brief\nbody\n")
    b = load_brief(p)
    assert b.business_model == "plg_freemium_directory"
    assert b.success_definition == "compounding_product"
    from pipeline.stages import get_stage
    txt = render(get_stage("market"), b, {})
    assert "plg_freemium_directory" in txt
    assert "compounding_product" in txt or "compounding" in txt.lower()


def test_common_block_has_flexibility_rules(tmp_path):
    from pipeline.prompts import load_brief, PROMPT_DIR
    common = (PROMPT_DIR / "_common.md").read_text().lower()
    assert "business model" in common
    assert "substitute" in common and "complement" in common
    assert "already doing" in common or "incumbent" in common  # disconfirmation check
    assert "re-scope" in common or "rescope" in common or "narrow the thesis" in common


def test_market_prompt_has_blue_ocean_and_noncustomers(tmp_path):
    from pipeline.prompts import PROMPT_DIR
    m = (PROMPT_DIR / "market.md").read_text().lower()
    assert "errc" in m and ("blue ocean" in m or "value innovation" in m)
    assert "noncustomer" in m or "non-customer" in m


def test_market_schema_has_errc_and_noncustomer_fields():
    from pipeline.prompts import load_schema
    from pipeline.stages import get_stage
    props = load_schema(get_stage("market"))["properties"]
    assert "errc_grid" in props and "noncustomer_tiers" in props


def test_render_injects_validation_mode(tmp_path):
    from pipeline.prompts import load_brief
    from pipeline.stages import get_stage
    p = tmp_path / "i.md"
    p.write_text("---\nslug: i\nvalidation_mode: new_market\n---\n# Idea brief\nbody\n")
    b = load_brief(p)
    assert b.validation_mode == "new_market"
    txt = render(get_stage("problem"), b, {})
    assert "new_market" in txt or "new market" in txt.lower()
