from server.keystore import KeyStore
from server.palgu_session import DeviceLogin

ACCOUNT = {"account": {"email": "a@b.com"}, "org": {"name": "Acme", "plan": "pro"}}


class FakeHttp:
    def __init__(self, device, token_steps):
        self._device = device
        self._tokens = list(token_steps)

    def post(self, path, body):
        if path.endswith("/auth/device/code"):
            return {"ok": True, "status": 200, "body": self._device}
        return self._tokens.pop(0)

    def get(self, path, key):
        return {"ok": True, "status": 200, "body": ACCOUNT}


DEVICE = {"device_code": "dc", "user_code": "WX-YZ", "interval": 1, "expires_in": 600}
APPROVED = {"ok": True, "status": 200, "body": {"access_token": "srt_live", **ACCOUNT}}
PENDING = {"ok": False, "status": 400, "body": {"error": "authorization_pending"}}
DENIED = {"ok": False, "status": 400, "body": {"error": "access_denied"}}


def test_start_returns_device_fields():
    dl = DeviceLogin(KeyStore(), http=FakeHttp(DEVICE, []), sleep=lambda s: None)
    start = dl.start()
    assert start["device_code"] == "dc" and start["user_code"] == "WX-YZ"


def test_poll_stores_key_on_approval():
    ks = KeyStore()
    dl = DeviceLogin(ks, http=FakeHttp(DEVICE, [PENDING, APPROVED]), sleep=lambda s: None)
    assert dl.poll("sess", DEVICE) is True
    assert ks.get("sess") == "srt_live"


def test_poll_stops_on_denied():
    ks = KeyStore()
    dl = DeviceLogin(ks, http=FakeHttp(DEVICE, [DENIED]), sleep=lambda s: None)
    assert dl.poll("sess", DEVICE) is False
    assert ks.has("sess") is False


def test_login_async_ok_then_thread_stores_key():
    ks = KeyStore()
    dl = DeviceLogin(ks, http=FakeHttp(DEVICE, [APPROVED]), sleep=lambda s: None)
    res = dl.login_async("sess")
    assert res["ok"] is True and "connect?code=WX-YZ" in res["text"]
    res["thread"].join(timeout=5)
    assert ks.get("sess") == "srt_live"


def test_login_async_reports_failed_start():
    dl = DeviceLogin(KeyStore(), http=FakeHttp({}, []), sleep=lambda s: None)
    res = dl.login_async("sess")
    assert res["ok"] is False and res["thread"] is None


def test_status_signed_in_and_out():
    ks = KeyStore()
    dl = DeviceLogin(ks, http=FakeHttp(DEVICE, []), sleep=lambda s: None)
    assert "not signed in" in dl.status("sess")
    ks.set("sess", "srt_live")
    assert "a@b.com" in dl.status("sess")
