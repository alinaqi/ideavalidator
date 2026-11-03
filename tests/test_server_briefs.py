from server.briefs import write_pitch_brief
from pipeline.prompts import load_brief


def test_write_pitch_brief_slug_and_content(tmp_path):
    slug, path = write_pitch_brief(tmp_path, "SMS waitlist that fills dental cancellations")
    assert slug and len(slug) <= 40 and slug == slug.lower()
    assert path.exists()
    brief = load_brief(path)
    assert brief.slug == slug
    assert "SMS waitlist" in path.read_text()


def test_write_pitch_brief_handles_long_messy_pitch(tmp_path):
    slug, path = write_pitch_brief(tmp_path, "A" * 300 + " !!! weird?? chars")
    assert 0 < len(slug) <= 40 and "/" not in slug and " " not in slug
