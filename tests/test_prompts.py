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
