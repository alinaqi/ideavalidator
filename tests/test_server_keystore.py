from pathlib import Path

from server.keystore import KeyStore, settings_for


def test_keystore_set_get_has_clear():
    ks = KeyStore()
    assert ks.has("s1") is False and ks.get("s1") is None
    ks.set("s1", "srt_abc")
    assert ks.has("s1") is True and ks.get("s1") == "srt_abc"
    ks.clear("s1")
    assert ks.has("s1") is False


def test_keystore_isolates_sessions():
    ks = KeyStore()
    ks.set("a", "srt_a"); ks.set("b", "srt_b")
    assert ks.get("a") == "srt_a" and ks.get("b") == "srt_b"


def test_settings_for_builds_palgu_provider(tmp_path):
    s = settings_for("srt_live", tmp_path)
    assert s.provider == "palgu" and s.api_key == "srt_live"
    assert s.palgu_base.endswith("/v1") and s.root == Path(tmp_path)
