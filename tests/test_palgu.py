from pipeline import palgu


def test_client_id_is_ideavalidator():
    assert palgu.CLIENT_ID == "ideavalidator"
    assert palgu.PALGU_ORIGIN == "https://api.palgu.ai"
    assert palgu.PALGU_V1 == "https://api.palgu.ai/v1"


def test_parse_arg():
    assert palgu.parse_arg("login") == "login"
    assert palgu.parse_arg(" STATUS ") == "status"
    assert palgu.parse_arg("nonsense") == "help"


def test_device_and_token_bodies():
    d = palgu.device_body("Claude Code on mac", "iid-1")
    assert d["client_id"] == "ideavalidator" and d["device"]["install_id"] == "iid-1"
    t = palgu.token_body("devcode")
    assert t["device_code"] == "devcode" and t["grant_type"].endswith("device_code")


def test_device_name_sanitises_and_caps():
    assert palgu.device_name("mac<>\x00") == "Claude Code on mac"
    assert len(palgu.device_name("x" * 200)) <= 64


def test_new_install_id_is_uuid_shape():
    iid = palgu.new_install_id(lambda: 0.5)
    assert len(iid) == 36 and iid.count("-") == 4 and iid[14] == "4"


def test_token_step_ok_returns_key():
    res = {"ok": True, "status": 200, "body": {"access_token": "srt_abc",
           "account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "free"}}}
    step = palgu.token_step(res, 5)
    assert step["state"] == "ok" and step["key"] == "srt_abc" and step["email"] == "a@b.com"


def test_token_step_pending_waits():
    assert palgu.token_step({"ok": False, "status": 400, "body": {"error": "authorization_pending"}}, 5) == {"state": "wait", "interval": 5}


def test_token_step_slow_down_adds_five():
    assert palgu.token_step({"ok": False, "status": 400, "body": {"error": "slow_down"}}, 5)["interval"] == 10


def test_token_step_expired_stops():
    s = palgu.token_step({"ok": False, "status": 400, "body": {"error": "expired_token"}}, 5)
    assert s["state"] == "stop" and "expired" in s["reason"]


def test_start_text_has_connect_url_and_code():
    t = palgu.start_text({"user_code": "WDJB-MJHT", "expires_in": 600})
    assert "www.palgu.ai/connect?code=WDJB-MJHT" in t and "WDJB-MJHT" in t


def test_status_text_states():
    assert "not signed in" in palgu.status_text(None)
    me = {"account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "pro"}}
    assert "a@b.com" in palgu.status_text(me) and "Acme" in palgu.status_text(me)
