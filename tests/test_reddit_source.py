from pipeline import reddit_source as rs


def test_reddit_empty_without_creds():
    assert rs.reddit_api("survey tool", {}) == []


def test_reddit_empty_when_token_fails(monkeypatch):
    monkeypatch.setattr(rs, "_token", lambda keys: None)
    assert rs.reddit_api("survey tool", {"REDDIT_CLIENT_ID": "c", "REDDIT_CLIENT_SECRET": "s"}) == []


def test_reddit_parses_search(monkeypatch):
    monkeypatch.setattr(rs, "_token", lambda keys: "tok")
    monkeypatch.setattr(rs, "_search_json", lambda token, q, ua: {"data": {"children": [
        {"data": {"title": "online survey tool?", "num_comments": 36, "subreddit": "ProductivityApps",
                  "permalink": "/r/ProductivityApps/comments/x/"}},
        {"data": {"title": "", "num_comments": 1, "subreddit": "x", "permalink": "/y"}}]}})
    out = rs.reddit_api("survey tool", {"REDDIT_CLIENT_ID": "c", "REDDIT_CLIENT_SECRET": "s"})
    assert len(out) == 1  # the empty-title row is dropped
    s = out[0]
    assert s.source == "reddit" and s.kind == "social" and s.value == 36
    assert s.detail == "r/ProductivityApps"
    assert s.url == "https://www.reddit.com/r/ProductivityApps/comments/x/"
