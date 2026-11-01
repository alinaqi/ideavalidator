from pipeline.categories import (CATEGORIES, MODELS, Category, catalog_for_prompt,
                                 get, list_categories)


def test_taxonomy_nonempty_and_keys_unique():
    keys = [c.key for c in list_categories()]
    assert len(keys) == len(set(keys)) >= 12
    assert "dev_tools_api" in keys
    assert "ai_action_layer" in keys  # the phrok category


def test_every_category_well_formed():
    for c in list_categories():
        assert isinstance(c, Category)
        assert c.name and c.description and c.incumbents
        assert c.models and isinstance(c.models, tuple)
        assert c.validation_note


def test_get_returns_category_or_raises():
    assert get("marketplace").key == "marketplace"
    import pytest
    with pytest.raises(KeyError):
        get("not_a_category")


def test_models_archetypes_cover_innovation_options():
    joined = " ".join(MODELS).lower()
    for token in ("usage", "subscription", "freemium", "marketplace", "open-core", "outcome"):
        assert token in joined


def test_catalog_for_prompt_lists_categories_and_models():
    text = catalog_for_prompt()
    assert "dev tools" in text.lower() or "developer" in text.lower()
    assert "connector" in text.lower()
    assert "CATEGORIES" in text and "BUSINESS MODEL" in text.upper()
    assert len(text) < 6000  # compact enough to inject into a prompt
