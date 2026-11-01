from pipeline import signals_sources as src


def test_dataforseo_empty_without_creds():
    assert src.dataforseo_volume(["survey creator"], {}) == []


def test_dataforseo_parses_volume(monkeypatch):
    monkeypatch.setattr(src, "_post_json", lambda u, h, p: {
        "tasks": [{"result": [
            {"keyword": "survey creator", "search_volume": 5400},
            {"keyword": "nps tool", "search_volume": 210}]}]})
    out = src.dataforseo_volume(["survey creator", "nps tool"],
                                {"DATAFORSEO_LOGIN": "l", "DATAFORSEO_PASSWORD": "p"})
    assert {s.label for s in out} == {"survey creator", "nps tool"}
    assert any(s.value == 5400 for s in out) and all(s.kind == "search_volume" for s in out)


def test_apify_empty_without_token():
    assert src.apify_reddit("survey tool", {}) == []


def test_apify_parses_items(monkeypatch):
    monkeypatch.setattr(src, "_post_json", lambda u, h, p: [
        {"title": "Best survey tool?", "numberOfComments": 14, "url": "https://reddit.com/x"},
        {"title": "Survey SaaS rec", "numberOfComments": 3, "url": "https://reddit.com/y"}])
    out = src.apify_reddit("survey tool", {"APIFY_TOKEN": "t"})
    assert len(out) == 2 and out[0].source == "apify" and out[0].kind == "social"
    assert out[0].value == 14 and out[0].url.startswith("https://reddit.com")


def test_grok_empty_without_key():
    assert src.grok_x("survey tool", {}) == []


def test_grok_parses_content(monkeypatch):
    monkeypatch.setattr(src, "_post_json", lambda u, h, p: {
        "choices": [{"message": {"content": "7 posts discuss survey creators on X this month."}}]})
    out = src.grok_x("survey tool", {"XAI_API_KEY": "k"})
    assert len(out) == 1 and out[0].source == "grok" and out[0].value == 7


def test_default_fetchers_combines_social(monkeypatch):
    monkeypatch.setattr(src, "apify_reddit", lambda q, k: [
        src.Signal("apify", "social", "r", 2, "", "u")])
    monkeypatch.setattr(src, "grok_x", lambda q, k: [
        src.Signal("grok", "social", "x", 5, "", "")])
    f = src.default_fetchers()
    social = f.social("q", {"APIFY_TOKEN": "t", "XAI_API_KEY": "k"})
    assert {s.source for s in social} == {"apify", "grok"}


def test_bad_json_degrades_to_empty(monkeypatch):
    monkeypatch.setattr(src, "_post_json", lambda u, h, p: None)
    assert src.dataforseo_volume(["k"], {"DATAFORSEO_LOGIN": "l", "DATAFORSEO_PASSWORD": "p"}) == []


def test_social_prefers_reddit_api_over_apify(monkeypatch):
    from pipeline import reddit_source
    monkeypatch.setattr(reddit_source, "reddit_api",
                        lambda q, k: [src.Signal("reddit", "social", "r", 3, "", "u")])
    monkeypatch.setattr(src, "apify_reddit",
                        lambda q, k: [src.Signal("apify", "social", "a", 1, "", "")])
    monkeypatch.setattr(src, "grok_x", lambda q, k: [])
    social = src.default_fetchers().social("q", {})
    assert {s.source for s in social} == {"reddit"}  # apify is only a fallback


def test_social_falls_back_to_apify_when_reddit_empty(monkeypatch):
    from pipeline import reddit_source
    monkeypatch.setattr(reddit_source, "reddit_api", lambda q, k: [])
    monkeypatch.setattr(src, "apify_reddit",
                        lambda q, k: [src.Signal("apify", "social", "a", 1, "", "")])
    monkeypatch.setattr(src, "grok_x", lambda q, k: [])
    social = src.default_fetchers().social("q", {})
    assert {s.source for s in social} == {"apify"}
